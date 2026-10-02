"""F01 timeout: per-tool and per-agent asyncio wrappers (P03 T03.040, 16 §5.1).

On expiry the awaitable is cancelled and a `ToolTimeoutError` records the
label and limit; the runtime turns it into failure code `F01_TIMEOUT`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from sots.errors import ToolTimeoutError


async def with_timeout[T](
    awaitable: asyncio.Future[T] | Coroutine[Any, Any, T], timeout_s: float, label: str
) -> T:
    """Await with a deadline; expiry raises a recorded ToolTimeoutError."""
    try:
        return await asyncio.wait_for(awaitable, timeout_s)
    except TimeoutError as exc:
        raise ToolTimeoutError(f"{label} timed out after {timeout_s:g}s") from exc
