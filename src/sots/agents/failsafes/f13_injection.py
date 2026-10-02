"""F13 injection guard: strip imperative patterns from observations (P03 T03.052).

Observations are data, never instructions (R-EXP-04). Fetched text matching
the configured `settings.agents.injection_patterns` (case-insensitive) is
stripped, the hit is counted, and `F13_INJECTION_STRIPPED` is logged.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def strip_injections(text: str, patterns: list[str]) -> tuple[str, int]:
    """Remove pattern occurrences; returns (cleaned, hits). Logs when hit."""
    cleaned = text
    hits = 0
    for pattern in patterns:
        if not pattern.strip():
            continue
        found = re.findall(re.escape(pattern), cleaned, flags=re.IGNORECASE)
        if found:
            hits += len(found)
            cleaned = re.sub(re.escape(pattern), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if hits:
        logger.warning("F13_INJECTION_STRIPPED hits=%d", hits)
    return cleaned, hits
