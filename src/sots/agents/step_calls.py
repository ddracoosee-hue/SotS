"""Step calls and final-output repairs (W0 split of agents/base.py)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sots.agents.agent_prompts import split_prompt_ref
from sots.agents.context import AgentContext
from sots.agents.failsafes.f01_timeout import with_timeout
from sots.agents.failsafes.f02_retry import with_retry
from sots.agents.failsafes.f05_schema import check_output
from sots.agents.scratchpad import render_scratchpad
from sots.config import Settings
from sots.errors import ValidationFailedError
from sots.models.agents import AgentAction
from sots.providers import prompts as prompt_loader
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage.db import Connection


@dataclass(frozen=True)
class StepDeps:
    """Everything a step call needs besides the invocation context."""

    prompts_dir: Path
    conn: Connection
    settings: Settings
    routing: RoutingConfig
    registry: Mapping[str, LLMProvider]
    build_variables: Callable[[AgentContext], dict[str, str]]


async def step_call(
    ctx: AgentContext,
    scratchpad: str,
    pack: ContextPack,
    budget: BudgetNode,
    deps: StepDeps,
) -> tuple[AgentAction, str]:
    """One step-prompt call (F01 inside F02); returns action + prompt text."""
    card = ctx.card
    prompt_id, version = split_prompt_ref(card.prompts.step)
    variables = {"scratchpad": scratchpad, **deps.build_variables(ctx)}
    template = prompt_loader.load_prompt(deps.prompts_dir, prompt_id, version)
    user_text = template.render(variables)

    async def _call() -> AgentAction:
        return await with_timeout(
            call_structured(
                card.routing_task, prompt_id, variables, AgentAction,
                pack, ctx.run_id, conn=deps.conn, settings=deps.settings,
                routing=deps.routing, registry=deps.registry,
                budget=budget, prompts_dir=deps.prompts_dir,
                prompt_version=version,
            ),
            float(card.limits.timeout_s),
            f"agent {card.name} step call",
        )

    return await with_retry(_call), user_text


async def validate_with_repairs[OutT: BaseModel](
    ctx: AgentContext,
    output_model: type[OutT],
    payload: dict[str, Any] | None,
    prompt_text: str,
    pack: ContextPack,
    budget: BudgetNode,
    entries: list[dict[str, Any]],
    max_repairs: int,
    deps: StepDeps,
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
            scratchpad = render_scratchpad(entries) + "\n\n" + note
            action, text = await step_call(ctx, scratchpad, pack, budget, deps)
            if action.type == "final":
                current = action.final
    raise AssertionError("unreachable")  # pragma: no cover


async def postcondition_repair[OutT: BaseModel](
    ctx: AgentContext,
    output_model: type[OutT],
    reasons: list[str],
    pack: ContextPack,
    budget: BudgetNode,
    entries: list[dict[str, Any]],
    deps: StepDeps,
    check_postconditions: Callable[[OutT, AgentContext], list[str]],
) -> OutT:
    """T03.014: one retry of the final with the reasons, then fail."""
    note = (
        "Postconditions failed: " + "; ".join(reasons)
        + ". Reply with a corrected FINAL action."
    )
    scratchpad = render_scratchpad(entries) + "\n\n" + note
    action, text = await step_call(ctx, scratchpad, pack, budget, deps)
    if action.type != "final":
        raise ValidationFailedError("postcondition repair did not return FINAL")
    try:
        output = check_output(output_model, action.final, prompt_text=text)
    except ValidationFailedError as exc:
        raise ValidationFailedError(
            f"postcondition repair still invalid: {exc}"
        ) from exc
    remaining = check_postconditions(output, ctx)
    if remaining:
        raise ValidationFailedError(
            "postconditions still failing: " + "; ".join(remaining)
        )
    return output
