"""Passage trimming for fetched docs (P07 T07.032, 06 §4.4).

Paragraphs score by BM25-lite overlap with the claim + key facts; the best
fill 1500 tokens and the survivors keep their original order.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from sots.research.bm25 import score_texts

#: Token budget for one trimmed doc (06 §4.4).
MAX_PASSAGE_TOKENS = 1500


def _estimate(text: str) -> int:
    return math.ceil(len(text) / 4) if text else 0


def trim_passages(
    doc_text: str,
    claim: str,
    key_facts: list[str],
    *,
    max_tokens: int = MAX_PASSAGE_TOKENS,
    counter: Callable[[str], int] | None = None,
) -> str:
    """Best paragraphs first by score, returned in original order (06 §4.4)."""
    count = counter or _estimate
    paragraphs = [p.strip() for p in doc_text.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    query = "\n".join([claim, *key_facts])
    scores = score_texts(paragraphs, query)
    ranked = sorted(range(len(paragraphs)), key=lambda i: scores[i], reverse=True)
    kept: list[int] = []
    used = 0
    for index in ranked:
        cost = count(paragraphs[index])
        if used + cost <= max_tokens:
            kept.append(index)
            used += cost
    if not kept:
        # Even the best paragraph overflows: sentence-trim it alone.
        best = paragraphs[ranked[0]]
        sentences = [s for s in best.replace("\n", " ").split(". ") if s]
        kept_text: list[str] = []
        for sentence in sentences:
            candidate = ". ".join([*kept_text, sentence])
            if count(candidate) <= max_tokens:
                kept_text.append(sentence)
            else:
                break
        return ". ".join(kept_text)
    return "\n\n".join(paragraphs[i] for i in sorted(kept))
