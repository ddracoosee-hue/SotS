"""Anchor Registry queries (P04A T04A.003, 23 §2).

Matching is normalized (diacritics stripped, lowercase) over quoted phrases,
capitalized entity words, and long lowercase words: "Berridge", "Love Yourz",
and "chrēstos" (or "chrestos") all match their anchors.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from sots.models.foundation import BriefAnchor

_QUOTED_RE = re.compile(r"[\"“”‘’']([^\"“”‘’']{2,})[\"“”‘’']")  # noqa: RUF001
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_PHRASE_MEAT_RE = re.compile(r"[a-z]{3,}")
_MIN_LONG_WORD = 7
_MIN_ENTITY_WORD = 4

_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "that", "this", "these", "those",
    "what", "when", "then", "than", "into", "over", "under", "while", "there",
    "their", "have", "has", "were", "will", "would", "your", "you", "his",
    "her", "they", "our", "out", "about", "each", "every", "such", "only",
    "also", "just", "more", "most", "some", "any", "versus", "feeds",
    "modern", "label", "rate", "personal", "common", "gloss", "kind", "good",
    "easy", "wanting", "liking", "life", "better", "yours", "thing", "all",
    "one", "two", "six", "ten", "its",
})


def normalize(text: str) -> str:
    """NFD-strip diacritics + lowercase (ē → e, on both sides of a match)."""
    folded = unicodedata.normalize("NFD", text)
    return folded.encode("ascii", "ignore").decode("ascii").lower()


def _anchor_terms(anchor: BriefAnchor) -> tuple[set[str], set[str]]:
    """(quoted phrases, keywords) from the anchor text + media identity."""
    phrases = {normalize(m) for m in _QUOTED_RE.findall(anchor.text)}
    phrases = {
        p for p in phrases
        if p and p not in _STOPWORDS and _PHRASE_MEAT_RE.search(p)
    }
    keywords: set[str] = set()
    for word in _WORD_RE.findall(anchor.text):
        lowered = normalize(word)
        if not lowered or lowered in _STOPWORDS:
            continue
        if (word[0].isupper() and len(lowered) >= _MIN_ENTITY_WORD) or len(
            lowered
        ) >= _MIN_LONG_WORD:
            keywords.add(lowered)
    if anchor.media is not None:
        for field in (anchor.media.title, anchor.media.creator or ""):
            for word in _WORD_RE.findall(field):
                lowered = normalize(word)
                if not lowered or lowered in _STOPWORDS:
                    continue
                if (word[0].isupper() and len(lowered) >= _MIN_ENTITY_WORD) or len(
                    lowered
                ) >= _MIN_LONG_WORD:
                    keywords.add(lowered)
        if anchor.media.title:
            phrases.add(normalize(anchor.media.title))
    return phrases, keywords


class AnchorRegistry:
    """Queryable anchor set (built once per Foundation load)."""

    def __init__(self, anchors: Iterable[BriefAnchor]) -> None:
        self._anchors = list(anchors)
        self._by_id = {anchor.id: anchor for anchor in self._anchors}
        self._terms = {anchor.id: _anchor_terms(anchor) for anchor in self._anchors}

    def __len__(self) -> int:
        return len(self._anchors)

    def by_id(self, anchor_id: str) -> BriefAnchor | None:
        """The anchor with this id, if any."""
        return self._by_id.get(anchor_id)

    def by_chapter(self, chapter_id: str) -> list[BriefAnchor]:
        """Anchors whose id carries the chapter prefix (registry order)."""
        prefix = f"{chapter_id}."
        return [a for a in self._anchors if a.id.startswith(prefix)]

    def by_type(self, anchor_type: str) -> list[BriefAnchor]:
        """Anchors of one type (registry order)."""
        return [a for a in self._anchors if a.type == anchor_type]

    def reuse_hotspots(self) -> list[BriefAnchor]:
        """Anchors reused across chapters, most-reused first (23 §2)."""
        hot = [a for a in self._anchors if a.reuse]
        return sorted(hot, key=lambda a: (-len(a.reuse), a.id))

    def match_in_text(self, text: str) -> list[str]:
        """Anchor ids mentioned in `text` (phrases + keywords, normalized)."""
        haystack = normalize(text)
        if not haystack.strip():
            return []
        words = set(_WORD_RE.findall(haystack))
        matched: list[str] = []
        for anchor in self._anchors:
            phrases, keywords = self._terms[anchor.id]
            if any(phrase in haystack for phrase in phrases) or keywords & words:
                matched.append(anchor.id)
        return matched
