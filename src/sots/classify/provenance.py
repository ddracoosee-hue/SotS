"""Provenance classification from NL cues (P04A T04A.034, 25 §7.1).

Explicit [TAG] markers (from ingest) beat inferred cues at confidence 1.0.
Cue confidences below LOW_CONFIDENCE flag needs_review for the P06 queue.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from sots.ingest.provenance_markers import MarkerHit
from sots.models.unit import AuthorProvenance

#: Under this confidence the unit goes to the review queue (P06).
LOW_CONFIDENCE = 0.75

_CUES: tuple[tuple[re.Pattern[str], AuthorProvenance, float, bool], ...] = (
    (re.compile(r"\bi (?:saw|heard|read) this (?:on|in)\s+([^.,;!?]+)", re.IGNORECASE),
     "live_source", 0.7, True),
    (re.compile(r"\baccording to\s+([^.,;!?]+)", re.IGNORECASE),
     "live_source", 0.7, True),
    (re.compile(r"\b(?:heard|learned)\b.{0,40}?\bby\s+([^.,;!?]+)", re.IGNORECASE),
     "live_source", 0.7, True),
    (re.compile(r"\bwhat follows is my personal opinion\b", re.IGNORECASE),
     "opinion", 0.9, False),
    (re.compile(r"\bmy conviction is\b", re.IGNORECASE), "belief", 0.85, False),
    (re.compile(r"\bi believe\b", re.IGNORECASE), "belief", 0.8, False),
    (re.compile(r"\bin my (?:experience|memory)\b|\bi remember\b", re.IGNORECASE),
     "experience", 0.7, False),
    (re.compile(r"\bin my opinion\b", re.IGNORECASE), "opinion", 0.8, False),
)


class ProvenanceOut(BaseModel):
    """Provenance verdict for one unit (None provenance = no signal)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provenance: AuthorProvenance | None = None
    source_ref: str | None = None
    serial: str | None = None
    confidence: float = 0.0
    needs_review: bool = False


def classify_provenance(
    text: str, *, markers: MarkerHit | None = None
) -> ProvenanceOut:
    """Explicit markers first, then NL cues, then no signal (25 §7.1)."""
    serial = markers.serial if markers is not None else None
    if markers is not None and markers.provenance is not None:
        return ProvenanceOut(
            provenance=markers.provenance, source_ref=markers.source_ref,
            serial=serial, confidence=1.0, needs_review=False,
        )
    best: ProvenanceOut | None = None
    for pattern, provenance, confidence, takes_ref in _CUES:
        found = pattern.search(text)
        if found is None:
            continue
        candidate = ProvenanceOut(
            provenance=provenance,
            source_ref=found.group(1).strip() if takes_ref else None,
            serial=serial,
            confidence=confidence,
            needs_review=confidence < LOW_CONFIDENCE,
        )
        if best is None or candidate.confidence > best.confidence:
            best = candidate
    if best is not None:
        return best
    return ProvenanceOut(serial=serial)
