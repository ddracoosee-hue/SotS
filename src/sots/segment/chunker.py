"""Paragraph-first chunking with sentence-safe overlap (P05 T05.002, 04 §5).

Paragraphs pack greedily until the chunk reaches `target_tokens`; paragraphs
bigger than the target split on sentence boundaries. Each chunk after the
first reaches back over whole sentences for ~`overlap_tokens` of overlap.
Boundaries never land mid-sentence.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Sequence

from pydantic import BaseModel, ConfigDict

from sots.segment.sentences import split_sentences

Counter = Callable[[str], int]

_PARAGRAPH_RE = re.compile(r"[^\n]+(?:\n[^\n]+)*")


def estimate_tokens(text: str) -> int:
    """~4 chars per token, matching the provider counters."""
    return max(1, math.ceil(len(text) / 4)) if text else 0


class ChunkSpan(BaseModel):
    """One chunk's span; the stage turns these into Chunk rows."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int
    start_char: int
    end_char: int
    token_estimate: int


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """Non-blank line runs (blank lines are the separators)."""
    return [(m.start(), m.end()) for m in _PARAGRAPH_RE.finditer(text) if m.group(0).strip()]


def _units(text: str, target_tokens: int, counter: Counter) -> list[tuple[int, int]]:
    """Packing units: paragraphs, or sentences for oversized paragraphs."""
    sentences = split_sentences(text)
    units: list[tuple[int, int]] = []
    for start, end in _paragraph_spans(text):
        if counter(text[start:end]) <= target_tokens:
            units.append((start, end))
            continue
        piece = [(s, e) for s, e in sentences if s >= start and e <= end]
        units.extend(piece or [(start, end)])
    return units


def _overlap_start(
    sentences: Sequence[tuple[int, int]], core_start: int, overlap_tokens: int,
    counter: Counter, text: str,
) -> int:
    """Whole-sentence start reaching ~overlap_tokens before core_start."""
    if overlap_tokens <= 0:
        return core_start
    at = core_start
    covered = 0
    for start, end in reversed([s for s in sentences if s[1] <= core_start]):
        covered += counter(text[start:end])
        at = start
        if covered >= overlap_tokens:
            break
    return at


def chunk_document(
    text: str, target_tokens: int, overlap_tokens: int,
    *, counter: Counter | None = None,
) -> list[ChunkSpan]:
    """Split text into overlapping chunks (04 §5)."""
    count = counter or estimate_tokens
    if not text.strip() or target_tokens <= 0:
        return []
    units = _units(text, target_tokens, count)
    if not units:
        return []
    sentences = split_sentences(text)
    cores: list[tuple[int, int]] = []
    core_start = units[0][0]
    core_tokens = 0
    for start, end in units:
        core_tokens += count(text[start:end])
        if core_tokens >= target_tokens:
            cores.append((core_start, end))
            core_start = end
            core_tokens = 0
    if core_tokens:
        cores.append((core_start, units[-1][1]))
    spans: list[ChunkSpan] = []
    for index, (start, end) in enumerate(cores):
        if index:
            start = _overlap_start(sentences, start, overlap_tokens, count, text)
        spans.append(ChunkSpan(
            index=index, start_char=start, end_char=end,
            token_estimate=count(text[start:end]),
        ))
    return spans
