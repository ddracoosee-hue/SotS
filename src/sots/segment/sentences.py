"""Sentence splitting with abbreviation guards (P05 T05.001, 04 §5).

Splits after `.`/`?`/`!` followed by whitespace + a capital (or end of text),
except after abbreviations. Title abbreviations (Mr., Dr.) and multi-dot ones
(U.S.) never split; other abbreviations (etc., Fig.) split only before a
capital. Returns (start, end) spans; `text[start:end]` is the sentence.
"""

from __future__ import annotations

import re

#: Abbreviations that never end a sentence (titles, initials, multi-dot).
_TITLE_ABBREVS = frozenset({
    "mr", "mrs", "ms", "dr", "st", "jr", "sr", "vs",
    "u.s", "u.k", "ph.d",
})
#: Abbreviations that end a sentence only before a capital letter.
_SOFT_ABBREVS = frozenset({
    "e.g", "i.e", "etc", "fig", "no", "vol", "pp", "ch", "sec", "al", "ed",
})

_TERMINAL_RE = re.compile(r"[?!]+|\.(?!\.)")
_CLOSERS = "\"'”’)]}"  # noqa: RUF001


def _token_before(text: str, dot: int) -> str:
    """Lowercased letters-and-dots token ending at `dot` (exclusive)."""
    start = dot
    while start > 0 and (text[start - 1].isalpha() or text[start - 1] == "."):
        start -= 1
    return text[start:dot].lower().rstrip(".")


def _after_closers(text: str, pos: int) -> int:
    """Skip closing quotes/brackets after terminal punctuation."""
    while pos < len(text) and text[pos] in _CLOSERS:
        pos += 1
    return pos


def _is_boundary(text: str, match: re.Match[str]) -> bool:
    """Whether this terminal punctuation ends a sentence."""
    end = _after_closers(text, match.end())
    rest = text[end:]
    stripped = rest.lstrip()
    if not stripped:
        return True  # end of text (trailing whitespace aside)
    if not rest[0].isspace():
        return False  # mid-word punctuation, e.g. "hello.World"
    following = stripped[0]
    starts_sentence = following.isupper() or following.isdigit()
    if match.group(0) != ".":
        return starts_sentence
    token = _token_before(text, match.start())
    if not token:
        prev = text[match.start() - 1] if match.start() > 0 else ""
        if prev.isdigit() and following.isdigit():
            return False  # decimals: 3.14
        return starts_sentence  # terminal dots after numbers; dot-runs
    if token in _TITLE_ABBREVS:
        return False
    if len(token) == 1 and token.isalpha():
        original = text[match.start() - 1]
        if original.isupper() and token != "i":
            return False  # initials (J. Cole); the word "I" still splits
    if token in _SOFT_ABBREVS:
        return following.isupper()  # etc./Fig: capitals only, never "Fig. 3"
    return starts_sentence


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Sentence (start, end) spans; leading whitespace stays outside spans."""
    if not text.strip():
        return []
    bounds = [match for match in _TERMINAL_RE.finditer(text) if _is_boundary(text, match)]
    spans: list[tuple[int, int]] = []
    start = 0
    for match in bounds:
        end = _after_closers(text, match.end())
        while start < end and text[start].isspace():
            start += 1
        if start < end:
            spans.append((start, end))
        start = end
    tail = len(text)
    head = start
    while head < tail and text[head].isspace():
        head += 1
    if head < tail:
        spans.append((head, tail))
    return spans
