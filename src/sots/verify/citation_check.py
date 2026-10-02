"""Deterministic citation check (P07 T07.031, 06 §3.4).

Whitespace/case-insensitive quotes and dashes are normalized on both sides;
an exact substring scores 100, else rapidfuzz `partial_ratio` must reach 90.
Excerpts under 20 characters always fail (too short to be evidence).
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

#: Minimum excerpt length (shorter strings are not evidence).
MIN_EXCERPT_CHARS = 20
#: Minimum fuzzy score to accept a non-exact excerpt (06 §3.4).
PARTIAL_THRESHOLD = 90.0

_QUOTES = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
})
_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-"})
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_citation(text: str) -> str:
    """Collapse whitespace; unify quotes and dashes (06 §3.4)."""
    unified = text.translate(_QUOTES).translate(_DASHES)
    return _WHITESPACE_RE.sub(" ", unified).strip()


def verify_excerpt(doc_text: str, excerpt: str) -> tuple[bool, float]:
    """Check an excerpt against its source text (06 §3.4)."""
    if len(excerpt) < MIN_EXCERPT_CHARS:
        return False, 0.0
    doc = normalize_citation(doc_text)
    quote = normalize_citation(excerpt)
    if not quote:
        return False, 0.0
    if quote in doc:
        return True, 100.0
    score = float(fuzz.partial_ratio(quote, doc))
    return score >= PARTIAL_THRESHOLD, score
