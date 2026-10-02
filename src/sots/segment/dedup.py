"""Cross-chunk overlap dedup (P05 T05.007, 04 §5).

Two units with overlapping document ranges and text similarity ≥ 90 keep the
one from the earlier chunk. Within a chunk, the earlier span wins ties.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from rapidfuzz import fuzz

from sots.models.enums import ContentType

#: Minimum text similarity (0-100) to collapse overlaps (04 §5).
SIMILARITY_THRESHOLD = 90.0


class DedupCandidate(BaseModel):
    """A unit placed in document coordinates, awaiting dedup."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    start_char: int
    end_char: int
    chunk_index: int
    content_type: ContentType | None = None
    classify_confidence: float | None = None


def _overlaps(first: DedupCandidate, second: DedupCandidate) -> bool:
    return max(first.start_char, second.start_char) < min(first.end_char, second.end_char)


def dedupe(candidates: list[DedupCandidate]) -> list[DedupCandidate]:
    """Collapse overlapping near-duplicates, earliest chunk wins (04 §5)."""
    kept: list[DedupCandidate] = []
    for candidate in sorted(candidates, key=lambda c: (c.chunk_index, c.start_char)):
        duplicate = any(
            _overlaps(candidate, other)
            and fuzz.ratio(candidate.text, other.text) >= SIMILARITY_THRESHOLD
            for other in kept
        )
        if not duplicate:
            kept.append(candidate)
    return kept
