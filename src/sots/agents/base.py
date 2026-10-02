"""Shared agent runtime: the fixed 7-step lifecycle (P03 T03.010-T03.015, 16 §2).

Every agent in every team runs through `BaseAgent.run`. Subclasses implement
only `build_step_variables()` and, optionally, `postconditions()`; the
runtime owns precheck, resume, the tool loop, validation, grading, and
persistence. No one-off agent loops (16 §2).

Failsafe wiring in this module: F01 (timeouts on step + tool calls), F02
(transient retries around both), F03 (per-tool circuits), F04 (loop
detection), F05 (final validation), F06 (checkpoints), F08 (dead letters),
F09 (watchdog heartbeats), F10 (budget slice), F13 (injection stripping),
F15 (observation caps), F16 (kill switch). F07/F11/F12/F18/F19/F20 live in
the persist/team/orchestrator layers that own their scope.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, cast

from pydantic import BaseModel

from sots.agents.agent_prompts import (
    pack_for_call,
    render_system_text,
    resolve_output_model,
)
from sots.agents.agent_state import restore_checkpoint, save_checkpoint
from sots.agents.context import AgentContext
from sots.agents.events import EventBus, emit_optional
from sots.agents.failsafes.f05_schema import check_output
from sots.agents.failsafes.f09_watchdog import Watchdog
from sots.agents.failsafes.f10_budget import agent_slice
from sots.agents.failsafes.f16_killswitch import is_stopped
from sots.agents.grading import Grader
from sots.agents.run_records import finish_run
from sots.agents.scratchpad import post_observation, render_scratchpad
from sots.agents.step_calls import (
    StepDeps,
    postcondition_repair,
    step_call,
    validate_with_repairs,
)
from sots.agents.tool_calls import BreakerPool, execute_tool, validate_tool_action
from sots.agents.tools.base import registered_tools
from sots.config import Settings
from sots.errors import (
    BudgetExceededError,
    ConfigError,
    LoopDetectedError,
    ToolNotAllowedError,
    ValidationFailedError,
)
from sots.models.agents import (
    AgentResult,
    Observation,
)
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.router import RoutingConfig
from sots.storage.db import Connection

logger = logging.getLogger(__name__)

MAX_INVALID_STREAK = 2  # T03.012: one invalid-step retry, then fail



class BaseAgent[InT: BaseModel, OutT: BaseModel](ABC):
    """The shared runtime. Subclass hooks: step variables + postconditions."""

    #: Validated final type. The subclass attribute wins; otherwise the
    #: card's `output_model` dotted path is imported (P14 owns real grading).
    output_model: ClassVar[type[BaseModel] | None] = None

    def __init__(
        self,
        *,
        settings: Settings,
        routing: RoutingConfig,
        registry: Mapping[str, LLMProvider],
        conn: Connection,
        prompts_dir: str | Path = "prompts",
        data_dir: str | Path = "data",
        grader: Grader | None = None,
        budget_parent: BudgetNode | None = None,
        bus: EventBus | None = None,
        watchdog: Watchdog | None = None,
    ) -> None:
        self._settings = settings
        self._routing = routing
        self._registry = registry
        self._conn = conn
        self._prompts_dir = Path(prompts_dir)
        self._data_dir = Path(data_dir)
        self._grader = grader
        self._budget_parent = budget_parent
        self._bus = bus
        self._watchdog = watchdog
        self._breakers = BreakerPool()

    @abstractmethod
    def build_step_variables(self, ctx: AgentContext) -> dict[str, str]:
        """Template variables for the card's step prompt (minus `scratchpad`)."""
        ...

    def postconditions(self, output: OutT, ctx: AgentContext) -> list[str]:
        """Reasons the final output is unacceptable (empty = pass)."""
        _ = (output, ctx)
        return []

    @staticmethod
    def _render_scratchpad(entries: list[dict[str, Any]]) -> str:
        """Tests call this directly; the logic lives in scratchpad.py."""
        return render_scratchpad(entries)

    def _post_observation(self, observation: Observation) -> dict[str, Any]:
        """Tests call this directly; the logic lives in scratchpad.py."""
        return post_observation(
            observation,
            injection_patterns=self._settings.agents.injection_patterns,
            max_chars=self._settings.agents.max_observation_chars,
        )

    async def run(self, ctx: AgentContext) -> AgentResult[OutT]:
        """The fixed lifecycle 1-7 (16 §2)."""
        card = ctx.card
        if self._watchdog is not None:
            self._watchdog.register(
                ctx.checkpoint_key, float(card.limits.timeout_s),
                card.limits.max_steps,
            )
        try:
            return await self._run_inner(ctx)
        finally:
            if self._watchdog is not None:
                self._watchdog.unregister(ctx.checkpoint_key)

    async def _run_inner(self, ctx: AgentContext) -> AgentResult[OutT]:
        """Lifecycle body (the watchdog wrapper lives in run())."""
        card = ctx.card
        started = datetime.now(UTC)
        # 1. PRECHECK
        if is_stopped(self._data_dir):
            return await finish_run(
                ctx, started, self._conn, self._bus, status="cancelled", failure_code="kill_switch",
                steps=0, error="kill switch engaged before start",
            )
        missing_tools = [t for t in card.tools if t not in registered_tools()]
        if missing_tools:
            return await finish_run(
                ctx, started, self._conn, self._bus, status="failed", failure_code="tools_missing",
                steps=0,
                error=f"card tools not registered: {', '.join(missing_tools)}",
            )
        output_model = cast(
            "type[OutT]", resolve_output_model(self.output_model, card)
        )
        system_text = render_system_text(self._prompts_dir, card)
        pack = pack_for_call(ctx, system_text)
        allowed_tokens = (
            ctx.budget.tokens_allowed
            if ctx.budget.tokens_allowed > 0
            else card.limits.max_tokens
        )
        allowed_cost = ctx.budget.cost_allowed if ctx.budget.cost_allowed > 0 else None
        budget = agent_slice(
            self._budget_parent, f"{card.name}:{ctx.checkpoint_key}",
            allowed_tokens, allowed_cost,
        )
        step_deps = StepDeps(
            prompts_dir=self._prompts_dir, conn=self._conn,
            settings=self._settings, routing=self._routing,
            registry=self._registry,
            build_variables=self.build_step_variables,
        )
        await emit_optional(
            self._bus, "agent.start", run_id=ctx.run_id,
            agent=card.name, payload={"act": ctx.act},
        )
        # 2. RESUME
        entries, done_steps, loop, invalid_streak = restore_checkpoint(
            self._conn, ctx.checkpoint_key
        )
        steps = done_steps
        # 3. LOOP
        final_payload: dict[str, Any] | None = None
        final_prompt_text = ""
        for step_no in range(done_steps + 1, card.limits.max_steps + 1):
            if is_stopped(self._data_dir):
                save_checkpoint(
                    self._conn, ctx.checkpoint_key, ctx.run_id, entries,
                    steps, loop, invalid_streak,
                )
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="cancelled",
                    failure_code="kill_switch",
                    steps=steps, error="kill switch engaged mid-run",
                )
            if self._watchdog is not None:
                self._watchdog.heartbeat(ctx.checkpoint_key)
            scratchpad = self._render_scratchpad(entries)
            try:
                action, user_text = await step_call(
                    ctx, scratchpad, pack, budget, step_deps
                )
            except BudgetExceededError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="degraded",
                    failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
                )
            steps = step_no
            await emit_optional(
                self._bus, "agent.step", run_id=ctx.run_id,
                agent=card.name,
                payload={"step": step_no, "action": action.type},
            )
            if action.type == "final":
                final_payload = action.final
                final_prompt_text = user_text
                save_checkpoint(
                    self._conn, ctx.checkpoint_key, ctx.run_id, entries,
                    steps, loop, invalid_streak,
                )
                break
            try:
                tool_name = validate_tool_action(ctx, action)
                loop.check_action(tool_name, action.args)
                breaker = self._breakers.for_tool(tool_name)
                observation = await execute_tool(
                    ctx, tool_name, action.args, settings=self._settings,
                    conn=self._conn, data_dir=str(self._data_dir),
                    breaker=breaker,
                )
            except ToolNotAllowedError as exc:
                invalid_streak += 1
                logger.warning("agent %s invalid step: %s", card.name, exc)
                if invalid_streak >= MAX_INVALID_STREAK:
                    return await finish_run(
                        ctx, started, self._conn, self._bus, status="failed",
                        failure_code="invalid_action",
                        steps=steps, error=str(exc),
                    )
                entries.append({
                    "tool": "runtime",
                    "content": f"invalid step (retry once): {exc}",
                    "truncated": False,
                })
                save_checkpoint(
                    self._conn, ctx.checkpoint_key, ctx.run_id, entries,
                    steps, loop, invalid_streak,
                )
                continue
            except LoopDetectedError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="degraded",
                    failure_code="F04_LOOP_DETECTED", steps=steps, error=str(exc),
                )
            entry = self._post_observation(observation)
            try:
                loop.check_observation(entry["content"])
            except LoopDetectedError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="degraded",
                    failure_code="F04_LOOP_DETECTED", steps=steps, error=str(exc),
                )
            entries.append(entry)
            invalid_streak = 0
            save_checkpoint(
                self._conn, ctx.checkpoint_key, ctx.run_id, entries,
                steps, loop, invalid_streak,
            )
            await emit_optional(
                self._bus, "agent.tool", run_id=ctx.run_id,
                agent=card.name,
                payload={"step": step_no, "tool": tool_name,
                         "ok": observation.ok},
            )
        else:
            return await finish_run(
                ctx, started, self._conn, self._bus, status="failed", failure_code="max_steps",
                steps=steps,
                error=f"no FINAL action within {card.limits.max_steps} steps",
            )
        # 4. VALIDATE
        try:
            output = await validate_with_repairs(
                ctx, output_model, final_payload, final_prompt_text, pack,
                budget, entries, card.limits.max_retries, step_deps,
            )
        except BudgetExceededError as exc:
            return await finish_run(
                ctx, started, self._conn, self._bus, status="degraded",
                failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
            )
        except ValidationFailedError as exc:
            return await finish_run(
                ctx, started, self._conn, self._bus, status="failed",
                failure_code="validation_failed",
                steps=steps, error=str(exc),
            )
        # 5. POSTCHECK
        reasons = self.postconditions(output, ctx)
        if reasons:
            try:
                output = await postcondition_repair(
                    ctx, output_model, reasons, pack, budget, entries,
                    step_deps, self.postconditions,
                )
            except BudgetExceededError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="degraded",
                    failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
                )
            except ValidationFailedError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="failed",
                    failure_code="postconditions_failed", steps=steps, error=str(exc),
                )
        # 6. GRADE
        grade_attempts = 0
        final_grade: float | None = None
        if card.grading.rubric:
            if self._grader is None:
                raise ConfigError(
                    f"agent {card.name!r} names rubric"
                    f" {card.grading.rubric!r} but no grader is wired"
                )
            decision = await self._grader.regeneration_loop(
                output.model_dump(mode="json"), card.grading.rubric,
                agent=card.name, run_id=ctx.run_id,
            )
            grade_attempts, final_grade = decision.attempts, decision.grade
            await emit_optional(
                self._bus, "agent.grade", run_id=ctx.run_id,
                agent=card.name,
                payload={"passed": decision.passed,
                         "grade": decision.grade},
            )
            if not decision.passed:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="failed",
                    failure_code="grade_failed",
                    steps=steps, error="grader rejected the output",
                    grade_attempts=grade_attempts, final_grade=final_grade,
                )
            try:
                output = check_output(output_model, decision.output, prompt_text="")
            except ValidationFailedError as exc:
                return await finish_run(
                    ctx, started, self._conn, self._bus, status="failed",
                    failure_code="grade_output_invalid", steps=steps, error=str(exc),
                    grade_attempts=grade_attempts, final_grade=final_grade,
                )
        # 7. PERSIST
        return await finish_run(
            ctx, started, self._conn, self._bus, status="ok", failure_code=None, steps=steps,
            output=output, grade_attempts=grade_attempts, final_grade=final_grade,
        )
