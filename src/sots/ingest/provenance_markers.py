"""Author-provenance markers (P04A T04A.034, 25 §7.1): explicit [TAGS].

Detected in ingest; the classifier (classify/provenance.py) combines these
with natural-language cues. First provenance marker wins; [SPIRAL] routing
combines with any provenance.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from sots.models.unit import AuthorProvenance

_LIVE_RE = re.compile(r"\[(?:LIVE|SOURCE)\s*:\s*([^\]]+)\]", re.IGNORECASE)
_BELIEF_RE = re.compile(r"\[(?:BELIEF|I BELIEVE)\]", re.IGNORECASE)
_EXPERIENCE_RE = re.compile(r"\[(?:EXPERIENCE|MEMORY)\]", re.IGNORECASE)
_OPINION_RE = re.compile(r"\[OPINION\]", re.IGNORECASE)
_SPIRAL_RE = re.compile(r"\[SPIRAL\]", re.IGNORECASE)
_TAG_RES: tuple[tuple[re.Pattern[str], AuthorProvenance], ...] = (
    (_BELIEF_RE, "belief"),
    (_EXPERIENCE_RE, "experience"),
    (_OPINION_RE, "opinion"),
)


class MarkerHit(BaseModel):
    """Explicit provenance markers found in the text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance: AuthorProvenance | None = None
    source_ref: str | None = None
    serial: str | None = None


def detect_markers(text: str) -> MarkerHit | None:
    """Explicit [TAG] provenance (None when the text has no markers)."""
    candidates: list[tuple[int, AuthorProvenance, str | None]] = []
    live = _LIVE_RE.search(text)
    if live is not None:
        candidates.append((live.start(), "live_source", live.group(1).strip()))
    for pattern, provenance in _TAG_RES:
        found = pattern.search(text)
        if found is not None:
            candidates.append((found.start(), provenance, None))
    spiral = _SPIRAL_RE.search(text) is not None
    if not candidates and not spiral:
        return None
    if not candidates:
        return MarkerHit(serial="provocation_spiral")
    _, provenance, source_ref = min(candidates, key=lambda item: item[0])
    return MarkerHit(
        provenance=provenance,
        source_ref=source_ref,
        serial="provocation_spiral" if spiral else None,
    )
