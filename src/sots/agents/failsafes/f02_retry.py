"""F02 retry with backoff via tenacity (P03 T03.041, 16 §5.1).

Transient errors (network timeouts, HTTP 429, HTTP 5xx) retry up to 3 times
with exponential backoff + jitter; anything else is raised immediately.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from sots.providers.transient import is_transient

__all__ = ["MAX_ATTEMPTS", "is_transient", "with_retry"]

MAX_ATTEMPTS = 4  # 1 initial try + 3 retries


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = MAX_ATTEMPTS,
    max_wait_s: float = 30.0,
) -> T:
    """Run `fn` with the F02 policy (transient-only retries, reraise last)."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_random_exponential(multiplier=0.5, max=max_wait_s),
        retry=retry_if_exception(is_transient),
        reraise=True,
    ):
        with attempt:
            return await fn()
    raise AssertionError("unreachable")  # pragma: no cover
