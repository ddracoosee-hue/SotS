"""Crisis-language safety scan (P06 T06.001, 05 §3.1, 01 R-PSY-04).

Batches of 20 units; flags set `safety_flag` and emit `author.input_needed`
with type `safety_notice`. The scan never blocks: it returns the flagged
unit ids and the pipeline continues.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.agents.events import EventBus
from sots.config import Settings
from sots.models.unit import Unit
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

#: Units per safety call (05 §3.1).
SAFETY_BATCH = 20
#: Standalone budget for one safety batch (medium in, tiny out).
SAFETY_BUDGET_TOKENS = 20_000


class SafetyFlag(BaseModel):
    """One flagged unit (05 §3.1 output model)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    reason: str


class SafetyScanOut(BaseModel):
    """The scan's structured output (05 §3.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    flags: list[SafetyFlag] = []


async def scan_batch(
    batch: Sequence[tuple[str, str]],
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
) -> SafetyScanOut:
    """Scan one batch of (unit_id, text) pairs (05 §3.1)."""
    pack = ContextPack(task="classify.safety_scan", system_role="", pieces=[])
    return await call_structured(
        "classify.safety_scan", "classify/safety_scan",
        {"units": "\n".join(f"{uid}: {text}" for uid, text in batch)},
        SafetyScanOut, pack, run_id, conn=conn, settings=settings,
        routing=routing, registry=providers,
        budget=BudgetNode("safety:batch", SAFETY_BUDGET_TOKENS),
        prompts_dir=prompts_dir, prompt_version=1,
    )


async def run_safety_scan(
    units: Sequence[Unit],
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    bus: EventBus | None = None,
) -> list[str]:
    """Flag crisis language over all units (non-blocking, 05 §3.1)."""
    by_id = {unit.id: unit for unit in units}
    flagged: list[str] = []
    for start in range(0, len(units), SAFETY_BATCH):
        batch = [(u.id, u.text) for u in units[start:start + SAFETY_BATCH]]
        out = await scan_batch(
            batch, run_id=run_id, conn=conn, settings=settings,
            routing=routing, providers=providers, prompts_dir=prompts_dir,
        )
        for flag in out.flags:
            unit = by_id.get(flag.unit_id)
            if unit is None or unit.id in flagged:
                continue  # hallucinated or repeated ids never block
            storage_repo.save_unit(conn, unit.model_copy(update={"safety_flag": True}))
            flagged.append(unit.id)
            if bus is not None:
                await bus.emit(
                    "author.input_needed", run_id=run_id,
                    payload={"type": "safety_notice", "unit_id": unit.id,
                             "reason": flag.reason},
                )
    return flagged
