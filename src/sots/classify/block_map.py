"""LLM block-mapping for unmarked dictation (P04A T04A.031, 23 §5)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.config import Settings
from sots.errors import ValidationFailedError
from sots.models.foundation import ChapterBrief
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage.db import Connection

#: Standalone budget for one mapping (short in, short out).
MAP_BUDGET_TOKENS = 20_000


class BlockMapOut(BaseModel):
    """Where an unmarked unit belongs (prompt null when unclear)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    block: int
    prompt_id: str | None = None
    confidence: float = 0.0


def render_blocks(brief: ChapterBrief) -> str:
    """Block cards for the mapper: purposes + prompt ids and texts."""
    chunks: list[str] = []
    for block in brief.blocks:
        prompts = "; ".join(f"{p.id}: {p.text}" for p in block.dictation_prompts)
        chunks.append(
            f"B{block.number} {block.name}: {block.structural_purpose} Prompts: {prompts}"
        )
    return "\n".join(chunks)


async def map_block(
    unit_text: str,
    chapter_id: str,
    brief: ChapterBrief,
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
) -> BlockMapOut:
    """Map unmarked text to (block, prompt?) using the Block Cards (23 §5)."""
    pack = ContextPack(task="classify.block_map", system_role="", pieces=[])
    mapped = await call_structured(
        "classify.block_map", "classify/block_map",
        {"chapter_id": chapter_id, "unit_text": unit_text,
         "blocks": render_blocks(brief)},
        BlockMapOut, pack, run_id, conn=conn, settings=settings,
        routing=routing, registry=providers,
        budget=BudgetNode(f"blockmap:{chapter_id}", MAP_BUDGET_TOKENS),
        prompts_dir=prompts_dir, prompt_version=1,
    )
    if mapped.block not in (1, 2, 3, 4, 5, 6):
        raise ValidationFailedError(f"block {mapped.block} out of range 1-6")
    if mapped.prompt_id is not None:
        known = {
            prompt.id for block in brief.blocks for prompt in block.dictation_prompts
        }
        if mapped.prompt_id not in known:
            raise ValidationFailedError(f"unknown prompt {mapped.prompt_id!r}")
        prompt_block = int(mapped.prompt_id.split(".")[1][1:])
        if prompt_block != mapped.block:
            raise ValidationFailedError(
                f"prompt {mapped.prompt_id} is not in block {mapped.block}"
            )
    return mapped
