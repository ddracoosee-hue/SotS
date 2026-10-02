"""F12 output sanity checks (P03 T03.051, 16 §5.1).

Rejects empty outputs, over-long outputs, wrong-language outputs (an English
stopword-ratio heuristic), repeated paragraphs (≥3 identical sentences), and
placeholder text. Returns violation codes; empty means clean.
"""

from __future__ import annotations

import re

DEFAULT_MAX_CHARS = 100000
MIN_WORDS_FOR_LANGUAGE = 20
MIN_STOPWORD_RATIO = 0.10
REPEAT_SENTENCES = 3

_STOPWORDS = frozenset(
    [
        "the", "a", "an", "and", "or", "of", "to", "in", "is", "it",
        "that", "this", "for", "on", "with", "as", "was", "were",
        "be", "been", "have", "has", "had", "not", "but", "at",
        "by", "from", "they", "we", "you", "he", "she", "it",
        "its", "our", "your", "their", "will", "would", "can",
        "could", "should", "there", "here", "when", "which",
        "who", "whom", "what", "where", "why", "all", "any",
        "each", "few", "more", "most", "other", "some", "such",
        "only", "own", "than", "too", "very",
    ]
)

_PLACEHOLDERS = ("lorem", "todo", "[insert")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z']+")


def check_text(text: str, *, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Violation codes for `text` (empty list = clean)."""
    violations: list[str] = []
    if not text.strip():
        return ["empty"]
    if len(text) > max_chars:
        violations.append("too_long")
    lowered = text.lower()
    if any(marker in lowered for marker in _PLACEHOLDERS):
        violations.append("placeholder")
    words = [w.lower() for w in _WORD.findall(text)]
    if len(words) >= MIN_WORDS_FOR_LANGUAGE:
        stopwords = sum(1 for w in words if w in _STOPWORDS)
        if stopwords / len(words) < MIN_STOPWORD_RATIO:
            violations.append("wrong_language")
    sentences = [
        " ".join(s.split()).lower()
        for s in _SENTENCE_SPLIT.split(text.strip())
        if len(s.strip()) > 10
    ]
    counts: dict[str, int] = {}
    for sentence in sentences:
        counts[sentence] = counts.get(sentence, 0) + 1
        if counts[sentence] >= REPEAT_SENTENCES:
            violations.append("repetition")
            break
    return violations
