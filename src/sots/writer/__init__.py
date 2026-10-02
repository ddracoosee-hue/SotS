"""Writer package stub (P00 T00.043).

Prose generation stays disabled until P11; :func:`draft` exists only so
callers fail loudly with :class:`WriterDisabledError`.
"""

from __future__ import annotations

from typing import Any

from sots.errors import WriterDisabledError


def draft(*args: Any, **kwargs: Any) -> Any:
    """Refuse to draft prose: the writer is disabled until P11."""
    raise WriterDisabledError("writer is disabled until P11 (Recheck & Reason)")
