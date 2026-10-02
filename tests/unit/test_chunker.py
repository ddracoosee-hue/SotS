"""P05 chunker tests (T05.002, 04 §5)."""

from __future__ import annotations

from itertools import pairwise

from sots.segment.chunker import ChunkSpan, chunk_document, estimate_tokens
from sots.segment.sentences import split_sentences

SENTENCE = "The quick brown fox jumps over the lazy dog near the river bank. "
PARA = SENTENCE * 6  # ~66 words, ~85 tokens


def _doc(paras: int) -> str:
    return "\n\n".join(f"{PARA} End of paragraph {n}." for n in range(paras))


def _boundary_ok(text: str, spans: list[ChunkSpan]) -> bool:
    """Every chunk edge sits on a sentence edge (never mid-sentence)."""
    edges: set[int] = set()
    for start, end in split_sentences(text):
        edges.add(start)
        edges.add(end)
    edges.add(0)
    edges.add(len(text))
    return all(s.start_char in edges and s.end_char in edges for s in spans)


def test_boundaries_and_overlap() -> None:
    """T05.002: sentence-safe edges, real sentence overlap between chunks."""
    text = _doc(12)
    spans = chunk_document(text, 300, 60)
    assert len(spans) > 2
    assert _boundary_ok(text, spans)
    assert spans[0].start_char == 0
    for prev, curr in pairwise(spans):
        assert curr.start_char < prev.end_char  # overlap exists
        assert curr.index == prev.index + 1
        shared = text[curr.start_char:prev.end_char]
        assert shared.strip()
        assert estimate_tokens(shared) >= 60 or curr.start_char == 0


def test_sizes_within_15_percent() -> None:
    """T05.002: non-final chunks land within ±15% of target."""
    text = _doc(20)
    spans = chunk_document(text, 300, 0)
    assert len(spans) > 2
    for span in spans[:-1]:
        ratio = span.token_estimate / 300
        assert 0.85 <= ratio <= 1.15, (span, ratio)
    assert _boundary_ok(text, spans)


def test_long_paragraph_splits_on_sentences() -> None:
    """One giant paragraph splits into sentence-safe chunks."""
    text = SENTENCE * 120
    spans = chunk_document(text, 300, 40)
    assert len(spans) > 2
    assert _boundary_ok(text, spans)
    assert spans[0].start_char == 0
    assert text[spans[-1].end_char:].strip() == ""  # only trailing space uncovered


def test_short_and_empty() -> None:
    """Short text is one chunk; blank text is none."""
    spans = chunk_document("Hello world. This is short.", 300, 60)
    assert len(spans) == 1
    assert (spans[0].start_char, spans[0].end_char) == (0, 27)
    assert chunk_document("", 300, 60) == []
    assert chunk_document("   \n\n  ", 300, 60) == []
