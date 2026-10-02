"""Stage 2 orchestration: chunk → extract → repair → cover → dedupe → store.

Chunk ids are deterministic (`{document_id}:c{index}`) so checkpoints survive
re-runs: a chunk with a checkpoint skips extraction and reuses its spans.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sots.config import Settings
from sots.models.document import Chunk
from sots.models.ids import new_id
from sots.models.unit import Unit
from sots.providers.base import LLMProvider
from sots.providers.router import RoutingConfig, resolve
from sots.segment.chunker import chunk_document
from sots.segment.coverage import cover_chunk
from sots.segment.dedup import DedupCandidate, dedupe
from sots.segment.extractor import RawUnit, extract_chunks
from sots.segment.offsets import UnitSpan, repair_units
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


def chunk_id_for(document_id: str, index: int) -> str:
    """Deterministic chunk id (stable across resume runs)."""
    return f"{document_id}:c{index:04d}"


def canonical_text(inbox_dir: str | Path, document_id: str) -> str:
    """The ingested canonical text Stage 2 segments."""
    path = Path(inbox_dir) / f"{document_id}.txt"
    return path.read_text(encoding="utf-8")


async def run_segment_stage(
    document_id: str,
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    inbox_dir: str | Path,
    prompts_dir: str | Path = "prompts",
) -> list[Unit]:
    """Segment one document into persisted, ordered units (05 Stage 2)."""
    text = canonical_text(inbox_dir, document_id)
    route = resolve("segment.extract_units", routing=routing, registry=providers)
    targets = settings.chunk.target_tokens
    target = getattr(targets, route.provider, targets.local)
    spans = chunk_document(text, target, settings.chunk.overlap_tokens)
    chunks = [
        Chunk(
            id=chunk_id_for(document_id, span.index), document_id=document_id,
            index=span.index, start_char=span.start_char, end_char=span.end_char,
            token_estimate=span.token_estimate,
        )
        for span in spans
    ]
    for chunk in chunks:
        storage_repo.save_chunk(conn, chunk)

    async def reextract(gap_text: str, gap_base: int) -> list[RawUnit]:
        return await _reextract(
            gap_text, gap_base, run_id, conn, settings, routing, providers,
            prompts_dir,
        )

    pending = [c for c in chunks if storage_repo.get_checkpoint(conn, c.id) is None]
    extracted = await extract_chunks(
        [(c.id, text[c.start_char:c.end_char], c.start_char) for c in pending],
        run_id=run_id, conn=conn, settings=settings, routing=routing,
        providers=providers, prompts_dir=prompts_dir,
    )
    by_span = {span.index: span for span in spans}
    repaired: dict[str, list[UnitSpan]] = {}
    for chunk in chunks:
        checkpoint = storage_repo.get_checkpoint(conn, chunk.id)
        if checkpoint is not None:
            repaired[chunk.id] = [
                UnitSpan.model_validate(s) for s in checkpoint["state"]["spans"]
            ]
            continue
        span = by_span[chunk.index]
        chunk_text = text[span.start_char:span.end_char]
        outcome = repair_units(chunk_text, extracted.get(chunk.id, []))
        for raw in outcome.dropped:
            storage_repo.append_event(conn, "segment.unmatched_unit", {
                "document_id": document_id, "chunk_id": chunk.id,
                "text": raw.text[:200],
            }, run_id=run_id)
        covered = await cover_chunk(
            chunk_text, outcome.repaired, reextract, base=span.start_char
        )
        repaired[chunk.id] = covered
        storage_repo.save_checkpoint(conn, chunk.id, {
            "spans": [s.model_dump(mode="json") for s in covered],
        }, run_id=run_id)

    chunk_index = {c.id: c.index for c in chunks}
    chunk_start = {c.id: c.start_char for c in chunks}
    candidates: list[DedupCandidate] = []
    for chunk in chunks:
        for unit_span in repaired[chunk.id]:
            base = chunk_start[chunk.id]
            candidates.append(DedupCandidate(
                text=unit_span.text,
                start_char=unit_span.start + base, end_char=unit_span.end + base,
                chunk_index=chunk_index[chunk.id],
                content_type=unit_span.content_type,
                classify_confidence=unit_span.classify_confidence,
            ))
    kept = dedupe(candidates)
    chunk_of_index = {c.index: c.id for c in chunks}
    units: list[Unit] = []
    for order, candidate in enumerate(sorted(kept, key=lambda c: c.start_char)):
        chunk_id = chunk_of_index[candidate.chunk_index]
        unit = Unit(
            id=new_id("unit"), document_id=document_id, chunk_id=chunk_id,
            run_id=run_id, order=order, text=candidate.text,
            start_char=candidate.start_char, end_char=candidate.end_char,
            content_type=candidate.content_type,
            classify_confidence=candidate.classify_confidence,
        )
        storage_repo.save_unit(conn, unit)
        units.append(unit)
    return units


async def _reextract(
    gap_text: str, gap_base: int, run_id: str, conn: Connection, settings: Settings,
    routing: RoutingConfig, providers: Mapping[str, LLMProvider], prompts_dir: str | Path,
) -> list[RawUnit]:
    """One re-extraction pass over an uncovered gap (offsets stay relative)."""
    out = await extract_chunks(
        [(f"gap:{gap_base}", gap_text, gap_base)], run_id=run_id, conn=conn,
        settings=settings, routing=routing, providers=providers,
        prompts_dir=prompts_dir, max_concurrency=1,
    )
    return out[f"gap:{gap_base}"]
