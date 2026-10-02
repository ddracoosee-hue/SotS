"""Stage 3 orchestration: safety scan, then classify (P06 T06.007, 05 §3).

Safety runs first in batches of 20; classification follows in batches with
bounded concurrency. Each finished unit (classified or FAILED) checkpoints
under its unit id, so resumes skip completed work. Author labels are never
touched. Embedded claims spawn depth-1 children re-classified as
FACTUAL_CLAIM.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.agents.events import EventBus
from sots.classify.classifier import classify_unit
from sots.classify.consistency import ClassificationOut
from sots.classify.embedded import spawn_children
from sots.classify.safety_scan import run_safety_scan
from sots.config import Settings
from sots.models.enums import ContentType
from sots.models.unit import Unit
from sots.providers.base import LLMProvider
from sots.providers.context_pack import ContextSources, PieceInput
from sots.providers.router import RoutingConfig
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

#: Neighbours on each side of the classified unit (pack piece 7).
NEIGHBOUR_RADIUS = 2
#: Instruction carried on embedded-child classifications (05 §3.3).
CHILD_NOTES = (
    "This is an embedded checkable claim extracted from a personal unit: "
    "it must classify as FACTUAL_CLAIM with a claim_kind."
)


class ClassifyReport(BaseModel):
    """What one stage run did (ids only; rows live in the database)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    classified: list[str]
    failed: list[str]
    children: list[str]
    flagged: list[str]
    skipped_author: list[str]


def _neighbour_text(units: list[Unit], position: int) -> str:
    """±2 order neighbours around `position`, excluding the unit itself."""
    lines: list[str] = []
    for offset in range(-NEIGHBOUR_RADIUS, NEIGHBOUR_RADIUS + 1):
        if offset == 0:
            continue
        neighbour = position + offset
        if 0 <= neighbour < len(units):
            lines.append(f"[{units[neighbour].order}] {units[neighbour].text}")
    return "\n".join(lines)


async def run_classify_stage(
    document_id: str,
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    bus: EventBus | None = None,
    profile_sources: ContextSources | None = None,
    max_concurrency: int | None = None,
    batch_size: int | None = None,
) -> ClassifyReport:
    """Safety-scan then classify every unit of one document (05 §3)."""
    units = sorted(
        storage_repo.list_units(conn, document_id=document_id),
        key=lambda unit: unit.order,
    )
    flagged = await run_safety_scan(
        units, run_id=run_id, conn=conn, settings=settings, routing=routing,
        providers=providers, prompts_dir=prompts_dir, bus=bus,
    )
    limit = max_concurrency
    if limit is None:
        limit = min(settings.concurrency.muse, settings.concurrency.local)
    semaphore = asyncio.Semaphore(max(1, limit))
    size = batch_size or settings.concurrency.batch_size

    classified: list[str] = []
    failed: list[str] = []
    children: list[str] = []
    skipped_author: list[str] = []

    async def _one(unit: Unit, position: int) -> None:
        if unit.labeled_by == "author":
            skipped_author.append(unit.id)
            return
        if storage_repo.get_checkpoint(conn, unit.id) is not None:
            classified.append(unit.id)
            return
        async with semaphore:
            base = profile_sources or ContextSources()
            sources = base.model_copy(update={"neighbours": PieceInput(
                text=_neighbour_text(units, position),
            )})
            out = await classify_unit(
                unit.id, unit.text, run_id=run_id, conn=conn, settings=settings,
                routing=routing, providers=providers, prompts_dir=prompts_dir,
                sources=sources,
            )
        if out is None:
            failed.append(unit.id)
            storage_repo.append_event(conn, "classify.failed", {
                "document_id": document_id, "unit_id": unit.id,
            }, run_id=run_id)
            storage_repo.save_checkpoint(conn, unit.id, {"status": "failed"},
                                         run_id=run_id)
            return
        _apply(conn, unit, out)
        classified.append(unit.id)
        if out.embedded_claims and unit.parent_unit_id is None:
            for child in spawn_children(unit, out.embedded_claims, run_id=run_id):
                storage_repo.save_unit(conn, child)
                await _classify_child(child, position)
                children.append(child.id)
        storage_repo.save_checkpoint(conn, unit.id, {"status": "classified"},
                                     run_id=run_id)

    async def _classify_child(child: Unit, position: int) -> None:
        async def _attempt(notes: str) -> ClassificationOut | None:
            async with semaphore:
                base = profile_sources or ContextSources()
                sources = base.model_copy(update={"neighbours": PieceInput(
                    text=_neighbour_text(units, position),
                )})
                return await classify_unit(
                    child.id, child.text, run_id=run_id, conn=conn,
                    settings=settings, routing=routing, providers=providers,
                    prompts_dir=prompts_dir, sources=sources, initial_notes=notes,
                )

        out = await _attempt(CHILD_NOTES)
        if out is not None and out.content_type != ContentType.FACTUAL_CLAIM:
            out = await _attempt(
                f"{CHILD_NOTES} Previous attempt wrongly returned"
                f" {out.content_type.value}; this embedded claim must be"
                " FACTUAL_CLAIM with a claim_kind."
            )
        if out is None or out.content_type != ContentType.FACTUAL_CLAIM:
            storage_repo.append_event(conn, "classify.failed", {
                "document_id": document_id, "unit_id": child.id,
            }, run_id=run_id)
            storage_repo.save_checkpoint(conn, child.id, {"status": "failed"},
                                         run_id=run_id)
            return
        _apply(conn, child, out, inherit_from=child.entities)
        storage_repo.save_checkpoint(conn, child.id, {"status": "classified"},
                                     run_id=run_id)

    for start in range(0, len(units), size):
        await asyncio.gather(*[
            _one(unit, position)
            for position, unit in enumerate(units[start:start + size], start=start)
        ])
    return ClassifyReport(
        document_id=document_id, classified=sorted(classified),
        failed=sorted(failed), children=sorted(children),
        flagged=sorted(flagged), skipped_author=sorted(skipped_author),
    )


def _apply(
    conn: Connection, unit: Unit, out: ClassificationOut,
    *, inherit_from: list[str] | None = None,
) -> None:
    """Persist a classification (children merge inherited entities first)."""
    entities = list(out.entities)
    if inherit_from:
        entities = [*inherit_from, *(e for e in entities if e not in inherit_from)]
    storage_repo.save_unit(conn, unit.model_copy(update={
        "content_type": out.content_type, "claim_kind": out.claim_kind,
        "media_kind": out.media_kind, "checkability": out.checkability,
        "entities": entities, "normalized_claim": out.normalized_claim,
        "classify_confidence": out.confidence,
    }))
