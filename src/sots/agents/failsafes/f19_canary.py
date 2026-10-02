"""F19 canary: prove Act I on one page before a big run (P03 T03.058, 16 §5.1).

Before a full run over `settings.canary.threshold_words` words, the caller
runs its act function against the canary fixture; an exception or an explicit
False aborts the run with CanaryFailedError. Disabled in settings or under
the threshold, this is a no-op returning None.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sots.config import Settings
from sots.errors import CanaryFailedError


async def maybe_run_canary[T](
    *, word_count: int, settings: Settings, act: Callable[[], Awaitable[T]]
) -> T | None:
    """Run the canary when due; abort the run on failure."""
    if not settings.canary.enabled or word_count <= settings.canary.threshold_words:
        return None
    try:
        result = await act()
    except Exception as exc:
        raise CanaryFailedError(f"canary run failed: {exc}") from exc
    if result is False:
        raise CanaryFailedError("canary run returned failure")
    return result


def canary_due(*, word_count: int, settings: Settings) -> bool:
    """True when a run of this size must canary first."""
    return settings.canary.enabled and word_count > settings.canary.threshold_words
