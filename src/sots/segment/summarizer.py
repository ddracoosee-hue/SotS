"""Summary-tree builder (P05 T05.009, 04 §5).

Level 0 holds one summary per chunk; groups of 8 roll up until a single
root remains. Summaries persist in `summaries` (kind `summary_tree`) with
(document_id, level, index, text, child_ids); ids are deterministic so
re-runs replace rather than duplicate.
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
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

#: Children rolled into one parent summary (04 §5).
GROUP_SIZE = 8
#: Hard cap on summary words (04 §5: ≤ 200).
MAX_WORDS = 200
#: Standalone budget for one summary call (medium in, short out).
SUMMARIZE_BUDGET_TOKENS = 20_000
#: The `summaries.kind` for tree nodes.
TREE_KIND = "summary_tree"


class ChunkSummaryOut(BaseModel):
    """One summary text (04 §5)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str


class SummaryTree(BaseModel):
    """The built tree: root id + per-level node counts."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    root_id: str
    level_counts: list[int]


def summary_id_for(document_id: str, level: int, index: int) -> str:
    """Deterministic tree-node id."""
    return f"{document_id}:sum:L{level}:{index}"


def fit_words(text: str, limit: int = MAX_WORDS) -> str:
    """Trim to `limit` words (the ≤200-word guarantee)."""
    words = text.split()
    return " ".join(words[:limit])


async def _summarize_text(
    text: str, level: int, *, run_id: str, conn: Connection, settings: Settings,
    routing: RoutingConfig, providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path, semaphore: asyncio.Semaphore,
) -> str:
    pack = ContextPack(task="summarize.chunk", system_role="", pieces=[])
    async with semaphore:
        out = await call_structured(
            "summarize.chunk", "summarize/summarize_chunk",
            {"level": str(level), "text": text},
            ChunkSummaryOut, pack, run_id, conn=conn, settings=settings,
            routing=routing, registry=providers,
            budget=BudgetNode(f"summarize:L{level}", SUMMARIZE_BUDGET_TOKENS),
            prompts_dir=prompts_dir, prompt_version=1,
        )
    return fit_words(out.text)


async def summarize_document(
    document_id: str,
    chunk_texts: Sequence[tuple[str, str]],
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    max_concurrency: int | None = None,
) -> SummaryTree:
    """Build + persist the summary tree for one document (04 §5)."""
    limit = max_concurrency
    if limit is None:
        limit = min(settings.concurrency.muse, settings.concurrency.local)
    semaphore = asyncio.Semaphore(max(1, limit))
    if not chunk_texts:
        raise ValueError("summarize_document needs at least one chunk")

    async def _level(
        texts: Sequence[str], level: int,
    ) -> list[str]:
        return list(await asyncio.gather(*[
            _summarize_text(
                text, level, run_id=run_id, conn=conn, settings=settings,
                routing=routing, providers=providers, prompts_dir=prompts_dir,
                semaphore=semaphore,
            )
            for text in texts
        ]))

    level = 0
    # Level 0: one summary per chunk; child_ids are the chunk ids.
    texts = await _level([text for _, text in chunk_texts], 0)
    level_counts: list[int] = []
    ids = [summary_id_for(document_id, 0, i) for i in range(len(texts))]
    for index, (node_id, text) in enumerate(zip(ids, texts, strict=True)):
        storage_repo.save_summary(
            conn, node_id, TREE_KIND,
            {"level": 0, "index": index, "text": text,
             "child_ids": [chunk_texts[index][0]]},
            run_id=run_id, document_id=document_id,
        )
    level_counts.append(len(ids))
    # Roll groups of 8 up until one root remains.
    current = list(zip(ids, texts, strict=True))
    while len(current) > 1:
        level += 1
        groups = [current[i:i + GROUP_SIZE] for i in range(0, len(current), GROUP_SIZE)]
        joined = ["\n\n".join(text for _, text in group) for group in groups]
        parents = await _level(joined, level)
        nxt: list[tuple[str, str]] = []
        for index, (group, parent) in enumerate(zip(groups, parents, strict=True)):
            node_id = summary_id_for(document_id, level, index)
            storage_repo.save_summary(
                conn, node_id, TREE_KIND,
                {"level": level, "index": index, "text": parent,
                 "child_ids": [child for child, _ in group]},
                run_id=run_id, document_id=document_id,
            )
            nxt.append((node_id, parent))
        level_counts.append(len(nxt))
        current = nxt
    return SummaryTree(
        document_id=document_id, root_id=current[0][0], level_counts=level_counts,
    )
