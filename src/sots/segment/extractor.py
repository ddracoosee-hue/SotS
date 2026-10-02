"""Unit extraction per chunk (P05 T05.004, 05 §2.2).

Calls `segment.extract_units` with the chunk text and an offset ruler; model
offsets are chunk-relative and always pass through offset repair before use.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.config import Settings
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage.db import Connection

#: Standalone budget for one chunk extraction (long in, medium out).
EXTRACT_BUDGET_TOKENS = 40_000


class RawUnit(BaseModel):
    """One model-proposed unit, offsets relative to the chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    start: int
    end: int


class ExtractUnitsOut(BaseModel):
    """The extractor's structured output (05 §2.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    units: list[RawUnit] = []


async def extract_chunk(
    chunk_id: str,
    chunk_text: str,
    chunk_start: int,
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
) -> list[RawUnit]:
    """Extract raw units from one chunk (05 §2.2)."""
    pack = ContextPack(task="segment.extract_units", system_role="", pieces=[])
    out = await call_structured(
        "segment.extract_units", "segment/extract_units",
        {"chunk_start": str(chunk_start), "chunk_text": chunk_text},
        ExtractUnitsOut, pack, run_id, conn=conn, settings=settings,
        routing=routing, registry=providers,
        budget=BudgetNode(f"extract:{chunk_id}", EXTRACT_BUDGET_TOKENS),
        prompts_dir=prompts_dir, prompt_version=1,
    )
    return list(out.units)


async def extract_chunks(
    chunks: Sequence[tuple[str, str, int]],
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    max_concurrency: int | None = None,
) -> dict[str, list[RawUnit]]:
    """Extract every chunk, at most `max_concurrency` calls in flight.

    Defaults to the tighter provider semaphore so neither backend is
    overwhelmed regardless of which provider the route resolves to.
    """
    limit = max_concurrency
    if limit is None:
        limit = min(settings.concurrency.muse, settings.concurrency.local)
    semaphore = asyncio.Semaphore(max(1, limit))

    async def _one(chunk_id: str, text: str, start: int) -> tuple[str, list[RawUnit]]:
        async with semaphore:
            units = await extract_chunk(
                chunk_id, text, start, run_id=run_id, conn=conn,
                settings=settings, routing=routing, providers=providers,
                prompts_dir=prompts_dir,
            )
        return chunk_id, units

    results = await asyncio.gather(*[
        _one(chunk_id, text, start) for chunk_id, text, start in chunks
    ])
    return dict(results)
