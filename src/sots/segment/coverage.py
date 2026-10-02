"""Coverage backstop (P05 T05.006, 05 §2.3).

Spans must cover ≥ 85% of the chunk's non-whitespace characters, else the
uncovered gaps are re-extracted once; whatever is still uncovered becomes
`NARRATIVE_DEVICE` fallback units (confidence 0) so no words are lost.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sots.models.enums import ContentType
from sots.segment.extractor import RawUnit
from sots.segment.offsets import UnitSpan, repair_units

#: Minimum non-whitespace coverage before the fallback (05 §2.3).
COVERAGE_THRESHOLD = 0.85

Reextract = Callable[[str, int], Awaitable[list[RawUnit]]]


def coverage_ratio(text: str, spans: list[UnitSpan]) -> float:
    """Fraction of non-whitespace chars covered by `spans`."""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 1.0
    covered = sum(1 for i, c in enumerate(text) if not c.isspace() and _covered(i, spans))
    return covered / len(chars)


def _covered(pos: int, spans: list[UnitSpan]) -> bool:
    return any(span.start <= pos < span.end for span in spans)


def uncovered_gaps(text: str, spans: list[UnitSpan]) -> list[tuple[int, int]]:
    """Maximal uncovered runs, trimmed to non-whitespace content."""
    gaps: list[tuple[int, int]] = []
    start: int | None = None
    for pos in range(len(text) + 1):
        open_gap = pos < len(text) and not _covered(pos, spans)
        if open_gap and start is None:
            start = pos
        elif not open_gap and start is not None:
            gaps.append((start, pos))
            start = None
    trimmed: list[tuple[int, int]] = []
    for gap_start, gap_end in gaps:
        while gap_start < gap_end and text[gap_start].isspace():
            gap_start += 1
        while gap_end > gap_start and text[gap_end - 1].isspace():
            gap_end -= 1
        if gap_start < gap_end:
            trimmed.append((gap_start, gap_end))
    return trimmed


def _shift(span: UnitSpan, base: int) -> UnitSpan:
    return UnitSpan(
        text=span.text, start=span.start + base, end=span.end + base,
        content_type=span.content_type, classify_confidence=span.classify_confidence,
    )


async def cover_chunk(
    chunk_text: str, spans: list[UnitSpan], reextract: Reextract, *, base: int = 0
) -> list[UnitSpan]:
    """Top spans up to full coverage: one re-extract, then fallbacks."""
    if coverage_ratio(chunk_text, spans) >= COVERAGE_THRESHOLD:
        return spans
    kept = list(spans)
    for gap_start, gap_end in uncovered_gaps(chunk_text, kept):
        gap_text = chunk_text[gap_start:gap_end]
        fresh = repair_units(gap_text, await reextract(gap_text, base + gap_start))
        kept.extend(_shift(span, gap_start) for span in fresh.repaired)
    for gap_start, gap_end in uncovered_gaps(chunk_text, kept):
        kept.append(UnitSpan(
            text=chunk_text[gap_start:gap_end], start=gap_start, end=gap_end,
            content_type=ContentType.NARRATIVE_DEVICE, classify_confidence=0.0,
        ))
    return kept
