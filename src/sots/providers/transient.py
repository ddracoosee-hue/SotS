"""Transient-error classification for F02 retries (P03 T03.041, 16 §5.1).

Lives in `providers/` because only that layer may name HTTP client types:
network timeouts, connection failures, HTTP 429, and HTTP 5xx are transient
and worth retrying; everything else fails fast.
"""

from __future__ import annotations

import httpx


def is_transient(exc: BaseException) -> bool:
    """True for network timeouts, connection failures, 429s, and 5xx responses."""
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False
