"""Canonical text normalization (P04 T04.011, 05 Stage 1).

Line endings to \\n, non-breaking spaces to plain spaces, 3+ blank lines to
2. Never alters words: spelling, punctuation, and typos stay exactly as the
author wrote them.
"""

from __future__ import annotations

import re

_BLANK_RUN = re.compile(r"\n{4,}")


def normalize_text(text: str) -> str:
    """Normalize endings, NBSP, and blank runs; words untouched (05 Stage 1)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    return _BLANK_RUN.sub("\n\n\n", text)
