"""BM25-lite relevance scoring shared by passages + supplements (06 §4.4).

Term frequency × inverse document frequency over caller-supplied texts;
higher is more relevant to the query. No external index, no stemming.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[a-z0-9]+")
#: Tokens shorter than this never score (noise, not signal).
MIN_TOKEN_LEN = 3


def query_terms(query: str) -> list[str]:
    """Lowercased content tokens from a query or claim."""
    return [w for w in _WORD_RE.findall(query.lower()) if len(w) >= MIN_TOKEN_LEN]


def score_texts(texts: list[str], query: str) -> list[float]:
    """One BM25-lite score per text, in input order (06 §4.4)."""
    terms = query_terms(query)
    if not terms or not texts:
        return [0.0] * len(texts)
    tokenized = [
        [w for w in _WORD_RE.findall(text.lower()) if len(w) >= MIN_TOKEN_LEN]
        for text in texts
    ]
    doc_freq = Counter(w for tokens in tokenized for w in set(tokens))
    count = len(tokenized)
    idf = {
        term: math.log(1 + (count - freq + 0.5) / (freq + 0.5))
        for term, freq in doc_freq.items()
    }
    scores: list[float] = []
    for tokens in tokenized:
        freq = Counter(tokens)
        scores.append(sum(freq[t] * idf.get(t, 0.0) for t in terms))
    return scores
