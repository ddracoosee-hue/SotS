"""Deterministic offset repair (P05 T05.005, 05 §2.3).

Step 1: claimed offsets verified. Step 2: exact search (one match → use it;
several → the first unused occurrence; all used → the unit is a duplicate
claim and drops). Step 3: rapidfuzz alignment ≥ 95, adopting the actual
substring. Step 4: drop, reported in `dropped` for `segment.unmatched_unit`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from rapidfuzz import fuzz

from sots.models.enums import ContentType
from sots.segment.extractor import RawUnit

#: Minimum alignment score to adopt a fuzzy span (05 §2.3).
FUZZY_THRESHOLD = 95.0


class UnitSpan(BaseModel):
    """A repaired unit span, offsets relative to the repaired text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    start: int
    end: int
    content_type: ContentType | None = None
    classify_confidence: float | None = None


class RepairOut(BaseModel):
    """Repaired spans plus the units that could not be placed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repaired: list[UnitSpan]
    dropped: list[RawUnit]


def _overlaps(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return max(first[0], second[0]) < min(first[1], second[1])


def _occurrences(haystack: str, needle: str) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    at = haystack.find(needle)
    while at >= 0:
        found.append((at, at + len(needle)))
        at = haystack.find(needle, at + 1)
    return found


def _claim(span: tuple[int, int], text: str, used: list[tuple[int, int]]) -> UnitSpan:
    used.append(span)
    return UnitSpan(text=text, start=span[0], end=span[1])


def repair_units(chunk_text: str, raw_units: list[RawUnit]) -> RepairOut:
    """Repair one chunk's raw units (05 §2.3, steps 1-4)."""
    repaired: list[UnitSpan] = []
    dropped: list[RawUnit] = []
    used: list[tuple[int, int]] = []
    for raw in raw_units:
        if not raw.text:
            dropped.append(raw)
            continue
        claimed = (raw.start, raw.end)
        if (
            0 <= raw.start <= raw.end <= len(chunk_text)
            and chunk_text[raw.start:raw.end] == raw.text
        ):
            repaired.append(_claim(claimed, raw.text, used))
            continue
        matches = _occurrences(chunk_text, raw.text)
        if matches:
            free = [m for m in matches if not any(_overlaps(m, u) for u in used)]
            if free:
                repaired.append(_claim(free[0], raw.text, used))
            else:
                dropped.append(raw)  # every occurrence already claimed: a dup
            continue
        aligned = fuzz.partial_ratio_alignment(raw.text, chunk_text)
        if aligned is not None and aligned.score >= FUZZY_THRESHOLD:
            span = (aligned.dest_start, aligned.dest_end)
            repaired.append(_claim(span, chunk_text[span[0]:span[1]], used))
        else:
            dropped.append(raw)
    return RepairOut(repaired=repaired, dropped=dropped)
