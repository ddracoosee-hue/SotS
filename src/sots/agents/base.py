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

import importlib
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from sots.agents.events import EventBus
from sots.agents.failsafes.f01_timeout import with_timeout
from sots.agents.failsafes.f02_retry import with_retry
from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f04_loop import LoopDetector
from sots.agents.failsafes.f05_schema import check_output
from sots.agents.failsafes.f06_checkpoint import load_state, save_state
from sots.agents.failsafes.f07_idempotency import idempotency_key, input_hash
from sots.agents.failsafes.f08_dead_letter import send as send_dead_letter
from sots.agents.failsafes.f09_watchdog import Watchdog
from sots.agents.failsafes.f10_budget import agent_slice
from sots.agents.failsafes.f13_injection import strip_injections
from sots.agents.failsafes.f15_size import cap_text
from sots.agents.failsafes.f16_killswitch import is_stopped
from sots.agents.grading import Grader
from sots.agents.tools.base import ToolContext, get_tool, registered_tools
from sots.config import Settings
from sots.errors import (
    BudgetExceededError,
    ConfigError,
    LoopDetectedError,
    ToolNotAllowedError,
    ValidationFailedError,
)
from sots.models.agents import (
    AgentAction,
    AgentCard,
    AgentResult,
    AgentRun,
    BudgetSlice,
    Observation,
)
from sots.providers import prompts as prompt_loader
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

logger = logging.getLogger(__name__)

_PROMPT_REF_RE = re.compile(r"^(.*)\.v(\d+)\.md$")
MAX_INVALID_STREAK = 2  # T03.012: one invalid-step retry, then fail


class AgentContext(BaseModel):
    """One agent invocation (16 §2). Built by the caller, consumed by run()."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    act: str
    card: AgentCard
    inputs: BaseModel
    context_pack: ContextPack
    budget: BudgetSlice
    checkpoint_key: str


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
        self._breakers: dict[str, CircuitBreaker] = {}

    @abstractmethod
    def build_step_variables(self, ctx: AgentContext) -> dict[str, str]:
        """Template variables for the card's step prompt (minus `scratchpad`)."""
        ...

    def postconditions(self, output: OutT, ctx: AgentContext) -> list[str]:
        """Reasons the final output is unacceptable (empty = pass)."""
        _ = (output, ctx)
        return []

    def _resolve_output_model(self, card: AgentCard) -> type[OutT]:
        """Subclass attribute first, else import the card's dotted path."""
        if self.output_model is not None:
            return cast("type[OutT]", self.output_model)
        module_name, dot, attr = card.output_model.rpartition(".")
        if not dot:
            raise ConfigError(
                f"agent {card.name!r} output_model {card.output_model!r}"
                " is not a dotted path"
            )
        try:
            module = importlib.import_module(module_name)
            resolved = getattr(module, attr)
        except (ImportError, AttributeError) as exc:
            raise ConfigError(
                f"agent {card.name!r} output_model {card.output_model!r}"
                f" cannot be imported: {exc}"
            ) from exc
        if not isinstance(resolved, type) or not issubclass(resolved, BaseModel):
            raise ConfigError(
                f"agent {card.name!r} output_model {card.output_model!r}"
                " is not a BaseModel subclass"
            )
        return cast("type[OutT]", resolved)

    @staticmethod
    def _split_prompt_ref(ref: str) -> tuple[str, int | None]:
        """`rewrite/step.v1.md` -> (id, version); unversioned -> (stem, None)."""
        match = _PROMPT_REF_RE.match(ref)
        if match:
            return match.group(1), int(match.group(2))
        stem = ref[:-3] if ref.endswith(".md") else ref
        return stem, None

    async def _emit(
        self,
        event_type: str,
        ctx: AgentContext,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Emit when a bus is wired; the loop never depends on observers."""
        if self._bus is not None:
            await self._bus.emit(
                event_type, run_id=ctx.run_id, agent=ctx.card.name,
                payload=payload or {},
            )

    def _breaker_for(self, tool_name: str) -> CircuitBreaker:
        """Per-tool F03 breaker, created lazily per invocation."""
        breaker = self._breakers.get(tool_name)
        if breaker is None:
            breaker = CircuitBreaker(f"tool:{tool_name}")
            self._breakers[tool_name] = breaker
        return breaker

    def _system_text(self, card: AgentCard) -> str:
        """Render the card's system prompt (takes no variables in P03)."""
        prompt_id, version = self._split_prompt_ref(card.prompts.system)
        template = prompt_loader.load_prompt(self._prompts_dir, prompt_id, version)
        return template.render({})

    def _pack_for_call(self, ctx: AgentContext, system_text: str) -> ContextPack:
        """Caller pack re-rooted at the card's system prompt (16 §2)."""
        role = ctx.context_pack.system_role.strip()
        combined = f"{system_text}\n\n{role}" if role else system_text
        return ContextPack(
            task=ctx.context_pack.task,
            system_role=combined,
            pieces=list(ctx.context_pack.pieces),
        )

    @staticmethod
    def _render_scratchpad(entries: list[dict[str, Any]]) -> str:
        """Observations wrapped as data (T03.011, R-EXP-04)."""
        blocks = [
            f"<observation tool=\"{entry['tool']}\">\n"
            f"{entry['content']}\n</observation>"
            for entry in entries
        ]
        return "\n\n".join(blocks)

    async def _step_call(
        self,
        ctx: AgentContext,
        scratchpad: str,
        pack: ContextPack,
        budget: BudgetNode,
    ) -> tuple[AgentAction, str]:
        """One step-prompt call (F01 inside F02); returns action + prompt text."""
        card = ctx.card
        prompt_id, version = self._split_prompt_ref(card.prompts.step)
        variables = {"scratchpad": scratchpad, **self.build_step_variables(ctx)}
        template = prompt_loader.load_prompt(self._prompts_dir, prompt_id, version)
        user_text = template.render(variables)

        async def _call() -> AgentAction:
            return await with_timeout(
                call_structured(
                    card.routing_task, prompt_id, variables, AgentAction,
                    pack, ctx.run_id, conn=self._conn, settings=self._settings,
                    routing=self._routing, registry=self._registry,
                    budget=budget, prompts_dir=self._prompts_dir,
                    prompt_version=version,
                ),
                float(card.limits.timeout_s),
                f"agent {card.name} step call",
            )

        return await with_retry(_call), user_text

    def _validate_tool_action(self, ctx: AgentContext, action: AgentAction) -> str:
        """Tool allow-list gate (T03.012); returns the tool name or raises."""
        if action.type != "tool" or not action.tool:
            raise ToolNotAllowedError("step action is not a usable tool call")
        if action.tool not in ctx.card.tools:
            raise ToolNotAllowedError(
                f"tool {action.tool!r} is not in card {ctx.card.name!r} allow-list"
            )
        available = registered_tools()
        if action.tool not in available:
            raise ConfigError(f"tool {action.tool!r} is allowed but not registered")
        return action.tool

    async def _execute_tool(
        self, ctx: AgentContext, tool_name: str, args: dict[str, Any] | None
    ) -> Observation:
        """Run one tool (F02 > F03 > F01); failures become ok=False observations."""
        tool = get_tool(tool_name)
        try:
            validated = tool.args_model.model_validate(args or {})
        except ValidationError as exc:
            raise ToolNotAllowedError(f"tool {tool_name!r} args invalid: {exc}") from exc
        tool_ctx = ToolContext(
            run_id=ctx.run_id,
            document_id=None,
            settings=self._settings,
            conn=self._conn,
            data_dir=str(self._data_dir),
        )
        breaker = self._breaker_for(tool_name)
        timeout_s = float(self._settings.agents.tool_timeout_s)

        async def _attempt() -> Observation:
            return await breaker.call(
                lambda: with_timeout(
                    tool.run(validated, tool_ctx), timeout_s, f"tool {tool_name}"
                )
            )

        try:
            return await with_retry(_attempt)
        except Exception as exc:
            return Observation(
                tool=tool_name, ok=False,
                content=f"error: {type(exc).__name__}: {exc}", truncated=False,
            )

    def _post_observation(self, observation: Observation) -> dict[str, Any]:
        """F13 strip + F15 cap; returns the scratchpad entry (T03.011)."""
        cleaned, _hits = strip_injections(
            observation.content, self._settings.agents.injection_patterns
        )
        kept, _note = cap_text(
            cleaned, self._settings.agents.max_observation_chars,
            f"observation:{observation.tool}",
        )
        return {"tool": observation.tool, "content": kept, "truncated": observation.truncated}

    def _checkpoint(
        self,
        ctx: AgentContext,
        entries: list[dict[str, Any]],
        step: int,
        loop: LoopDetector,
        invalid_streak: int,
    ) -> None:
        """F06 save after every step (kill + resume continue from here)."""
        save_state(
            self._conn, ctx.checkpoint_key, ctx.run_id,
            {
                "version": 1,
                "scratchpad": entries,
                "step": step,
                "loop": loop.snapshot(),
                "invalid_streak": invalid_streak,
            },
        )

    def _restore(
        self, ctx: AgentContext
    ) -> tuple[list[dict[str, Any]], int, LoopDetector, int]:
        """F06 resume; corrupt checkpoints restart from scratch (T03.045)."""
        entries: list[dict[str, Any]] = []
        loop = LoopDetector()
        try:
            state = load_state(self._conn, ctx.checkpoint_key)
        except Exception as exc:
            logger.warning("checkpoint %r corrupt, restarting: %s", ctx.checkpoint_key, exc)
            return [], 0, loop, 0
        if state is None:
            return [], 0, loop, 0
        raw_entries = state.get("scratchpad", [])
        if isinstance(raw_entries, list):
            entries = [e for e in raw_entries if isinstance(e, dict)]
        step = state.get("step", 0)
        step = step if isinstance(step, int) and step >= 0 else 0
        raw_loop = state.get("loop", {})
        if isinstance(raw_loop, dict):
            loop.restore(raw_loop)
        streak = state.get("invalid_streak", 0)
        streak = streak if isinstance(streak, int) and streak >= 0 else 0
        return entries, step, loop, streak

    def _run_usage(self, run_id: str) -> tuple[int, int, float]:
        """Sum this run's LLM calls from the call log (T03.013)."""
        calls = storage_repo.list_llm_calls(self._conn, run_id=run_id)
        return (
            sum(call.input_tokens for call in calls),
            sum(call.output_tokens for call in calls),
            sum(call.cost_estimate for call in calls),
        )

    async def _finish(
        self,
        ctx: AgentContext,
        started: datetime,
        *,
        status: Literal["ok", "failed", "degraded", "cancelled"],
        failure_code: str | None,
        steps: int,
        output: OutT | None = None,
        error: str | None = None,
        grade_attempts: int = 0,
        final_grade: float | None = None,
    ) -> AgentResult[OutT]:
        """PERSIST: AgentRun row, failure disposition, terminal event (T03.013)."""
        card = ctx.card
        final: Literal["ok", "failed", "dead_letter", "escalated", "degraded",
                       "cancelled"] = status
        if status == "failed":
            message = error or failure_code or "failed"
            if card.on_failure == "dead_letter":
                send_dead_letter(
                    self._conn, run_id=ctx.run_id, agent=card.name,
                    team=card.team,
                    payload={
                        "inputs": ctx.inputs.model_dump(mode="json"),
                        "failure_code": failure_code,
                    },
                    error=message,
                )
                final = "dead_letter"
            elif card.on_failure == "escalate_to_author":
                final = "escalated"
            else:
                final = "degraded"
        tokens_in, tokens_out, cost = self._run_usage(ctx.run_id)
        storage_repo.save_agent_run(
            self._conn,
            AgentRun(
                id=idempotency_key(
                    ctx.run_id, card.name,
                    input_hash(ctx.inputs.model_dump(mode="json")),
                ),
                run_id=ctx.run_id,
                agent=card.name,
                team=card.team,
                act=ctx.act,
                started_at=started,
                finished_at=datetime.now(UTC),
                steps=steps,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
                status=final,
                failure_code=failure_code,
                grade_attempts=grade_attempts,
                final_grade=final_grade,
                checkpoint_key=ctx.checkpoint_key,
            ),
        )
        if final != "cancelled":
            storage_repo.delete_checkpoint(self._conn, ctx.checkpoint_key)
        await self._emit(
            "agent.done" if final == "ok" else "agent.failed", ctx,
            {"status": final, "failure_code": failure_code, "steps": steps},
        )
        return AgentResult(
            agent=card.name, status=final, output=output, error=error
        )

    async def _validate_with_repairs(
        self,
        ctx: AgentContext,
        output_model: type[OutT],
        payload: dict[str, Any] | None,
        prompt_text: str,
        pack: ContextPack,
        budget: BudgetNode,
        entries: list[dict[str, Any]],
        max_repairs: int,
    ) -> OutT:
        """F05 validate, with repair rounds that request corrected finals."""
        current = payload
        text = prompt_text
        for repair_no in range(max_repairs + 1):
            try:
                return check_output(output_model, current, prompt_text=text)
            except ValidationFailedError as exc:
                if repair_no >= max_repairs:
                    raise
                note = (
                    f"Your final output was rejected (repair {repair_no + 1}):"
                    f" {exc} Reply with a corrected FINAL action."
                )
                scratchpad = self._render_scratchpad(entries) + "\n\n" + note
                action, text = await self._step_call(ctx, scratchpad, pack, budget)
                if action.type == "final":
                    current = action.final
        raise AssertionError("unreachable")  # pragma: no cover

    async def _postcondition_repair(
        self,
        ctx: AgentContext,
        output_model: type[OutT],
        reasons: list[str],
        pack: ContextPack,
        budget: BudgetNode,
        entries: list[dict[str, Any]],
    ) -> OutT:
        """T03.014: one retry of the final with the reasons, then fail."""
        note = (
            "Postconditions failed: " + "; ".join(reasons)
            + ". Reply with a corrected FINAL action."
        )
        scratchpad = self._render_scratchpad(entries) + "\n\n" + note
        action, text = await self._step_call(ctx, scratchpad, pack, budget)
        if action.type != "final":
            raise ValidationFailedError("postcondition repair did not return FINAL")
        try:
            output = check_output(output_model, action.final, prompt_text=text)
        except ValidationFailedError as exc:
            raise ValidationFailedError(
                f"postcondition repair still invalid: {exc}"
            ) from exc
        remaining = self.postconditions(output, ctx)
        if remaining:
            raise ValidationFailedError(
                "postconditions still failing: " + "; ".join(remaining)
            )
        return output

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
            return await self._finish(
                ctx, started, status="cancelled", failure_code="kill_switch",
                steps=0, error="kill switch engaged before start",
            )
        missing_tools = [t for t in card.tools if t not in registered_tools()]
        if missing_tools:
            return await self._finish(
                ctx, started, status="failed", failure_code="tools_missing",
                steps=0,
                error=f"card tools not registered: {', '.join(missing_tools)}",
            )
        output_model = self._resolve_output_model(card)
        system_text = self._system_text(card)
        pack = self._pack_for_call(ctx, system_text)
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
        await self._emit("agent.start", ctx, {"act": ctx.act})
        # 2. RESUME
        entries, done_steps, loop, invalid_streak = self._restore(ctx)
        steps = done_steps
        # 3. LOOP
        final_payload: dict[str, Any] | None = None
        final_prompt_text = ""
        for step_no in range(done_steps + 1, card.limits.max_steps + 1):
            if is_stopped(self._data_dir):
                self._checkpoint(ctx, entries, steps, loop, invalid_streak)
                return await self._finish(
                    ctx, started, status="cancelled", failure_code="kill_switch",
                    steps=steps, error="kill switch engaged mid-run",
                )
            if self._watchdog is not None:
                self._watchdog.heartbeat(ctx.checkpoint_key)
            scratchpad = self._render_scratchpad(entries)
            try:
                action, user_text = await self._step_call(
                    ctx, scratchpad, pack, budget
                )
            except BudgetExceededError as exc:
                return await self._finish(
                    ctx, started, status="degraded",
                    failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
                )
            steps = step_no
            await self._emit(
                "agent.step", ctx, {"step": step_no, "action": action.type}
            )
            if action.type == "final":
                final_payload = action.final
                final_prompt_text = user_text
                self._checkpoint(ctx, entries, steps, loop, invalid_streak)
                break
            try:
                tool_name = self._validate_tool_action(ctx, action)
                loop.check_action(tool_name, action.args)
                observation = await self._execute_tool(ctx, tool_name, action.args)
            except ToolNotAllowedError as exc:
                invalid_streak += 1
                logger.warning("agent %s invalid step: %s", card.name, exc)
                if invalid_streak >= MAX_INVALID_STREAK:
                    return await self._finish(
                        ctx, started, status="failed", failure_code="invalid_action",
                        steps=steps, error=str(exc),
                    )
                entries.append({
                    "tool": "runtime",
                    "content": f"invalid step (retry once): {exc}",
                    "truncated": False,
                })
                self._checkpoint(ctx, entries, steps, loop, invalid_streak)
                continue
            except LoopDetectedError as exc:
                return await self._finish(
                    ctx, started, status="degraded",
                    failure_code="F04_LOOP_DETECTED", steps=steps, error=str(exc),
                )
            entry = self._post_observation(observation)
            try:
                loop.check_observation(entry["content"])
            except LoopDetectedError as exc:
                return await self._finish(
                    ctx, started, status="degraded",
                    failure_code="F04_LOOP_DETECTED", steps=steps, error=str(exc),
                )
            entries.append(entry)
            invalid_streak = 0
            self._checkpoint(ctx, entries, steps, loop, invalid_streak)
            await self._emit(
                "agent.tool", ctx,
                {"step": step_no, "tool": tool_name, "ok": observation.ok},
            )
        else:
            return await self._finish(
                ctx, started, status="failed", failure_code="max_steps",
                steps=steps,
                error=f"no FINAL action within {card.limits.max_steps} steps",
            )
        # 4. VALIDATE
        try:
            output = await self._validate_with_repairs(
                ctx, output_model, final_payload, final_prompt_text, pack,
                budget, entries, card.limits.max_retries,
            )
        except BudgetExceededError as exc:
            return await self._finish(
                ctx, started, status="degraded",
                failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
            )
        except ValidationFailedError as exc:
            return await self._finish(
                ctx, started, status="failed", failure_code="validation_failed",
                steps=steps, error=str(exc),
            )
        # 5. POSTCHECK
        reasons = self.postconditions(output, ctx)
        if reasons:
            try:
                output = await self._postcondition_repair(
                    ctx, output_model, reasons, pack, budget, entries
                )
            except BudgetExceededError as exc:
                return await self._finish(
                    ctx, started, status="degraded",
                    failure_code="F10_BUDGET_EXHAUSTED", steps=steps, error=str(exc),
                )
            except ValidationFailedError as exc:
                return await self._finish(
                    ctx, started, status="failed",
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
            await self._emit(
                "agent.grade", ctx,
                {"passed": decision.passed, "grade": decision.grade},
            )
            if not decision.passed:
                return await self._finish(
                    ctx, started, status="failed", failure_code="grade_failed",
                    steps=steps, error="grader rejected the output",
                    grade_attempts=grade_attempts, final_grade=final_grade,
                )
            try:
                output = check_output(output_model, decision.output, prompt_text="")
            except ValidationFailedError as exc:
                return await self._finish(
                    ctx, started, status="failed",
                    failure_code="grade_output_invalid", steps=steps, error=str(exc),
                    grade_attempts=grade_attempts, final_grade=final_grade,
                )
        # 7. PERSIST
        return await self._finish(
            ctx, started, status="ok", failure_code=None, steps=steps,
            output=output, grade_attempts=grade_attempts, final_grade=final_grade,
        )
