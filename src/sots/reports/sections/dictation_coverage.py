"""Per-chapter dictation coverage (P04A T04A.033, 23 §5).

Prompts: answered (≥1 unit), partial (block has units, prompt has none),
missing (neither). Anchors: used (tagged on any unit) vs planned (in the
brief) vs unused.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from sots.models.foundation import ChapterBrief
from sots.models.unit import Unit


class PromptCoverage(BaseModel):
    """One prompt's coverage state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_id: str
    status: Literal["answered", "partial", "missing"]
    unit_ids: list[str]


class ChapterCoverage(BaseModel):
    """Whole-chapter dictation + anchor coverage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str
    prompts: list[PromptCoverage]
    anchors_used: list[str]
    anchors_planned: list[str]
    anchors_unused: list[str]


def _prompt_block(prompt_id: str) -> str | None:
    """`ch03.B2.P1` -> `ch03.B2` (None when malformed)."""
    parts = prompt_id.split(".")
    if len(parts) != 3 or not parts[1].startswith("B"):
        return None
    return f"{parts[0]}.{parts[1]}"


def chapter_coverage(brief: ChapterBrief, units: list[Unit]) -> ChapterCoverage:
    """Coverage of one brief against its keyed units (T04A.033)."""
    by_prompt: dict[str, list[str]] = {}
    blocks_with_units: set[str] = set()
    for unit in units:
        if unit.prompt_id is not None:
            by_prompt.setdefault(unit.prompt_id, []).append(unit.id)
            block = _prompt_block(unit.prompt_id)
            if block is not None:
                blocks_with_units.add(block)
    coverages: list[PromptCoverage] = []
    for block in brief.blocks:
        for prompt in block.dictation_prompts:
            unit_ids = by_prompt.get(prompt.id, [])
            if unit_ids:
                status: Literal["answered", "partial", "missing"] = "answered"
            elif f"{brief.chapter_id}.B{block.number}" in blocks_with_units:
                status = "partial"
            else:
                status = "missing"
            coverages.append(PromptCoverage(
                prompt_id=prompt.id, status=status, unit_ids=unit_ids
            ))
    planned = sorted({a for block in brief.blocks for a in block.anchors})
    used = sorted({a for unit in units for a in unit.anchor_ids})
    return ChapterCoverage(
        chapter_id=brief.chapter_id,
        prompts=coverages,
        anchors_used=used,
        anchors_planned=planned,
        anchors_unused=[a for a in planned if a not in set(used)],
    )
