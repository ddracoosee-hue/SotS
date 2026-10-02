"""F03 circuit breaker per provider/tool key (P03 T03.042, 16 §5.1).

closed → open after 5 consecutive failures → half-open after 60 s → closed
on the first success. While open, calls fail fast with CircuitOpenError so
the agent can use a fallback or degrade. The clock is injectable for tests.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar

from sots.errors import CircuitOpenError

T = TypeVar("T")

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    """One breaker; orchestrators keep one per provider/tool key."""

    def __init__(
        self,
        key: str,
        max_failures: int = 5,
        reset_s: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.key = key
        self.max_failures = max_failures
        self.reset_s = reset_s
        self._clock = clock
        self.state: State = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self._trial_in_flight = False

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Run `fn` through the breaker (fail fast while open)."""
        if self.state == "open":
            if self._clock() - self.opened_at >= self.reset_s:
                self.state = "half_open"
            else:
                raise CircuitOpenError(f"circuit {self.key!r} is open")
        if self.state == "half_open":
            if self._trial_in_flight:
                raise CircuitOpenError(f"circuit {self.key!r} trial already in flight")
            self._trial_in_flight = True
        try:
            result = await fn()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_failure(self) -> None:
        self._trial_in_flight = False
        if self.state == "half_open":
            self._trip()
            return
        self.failures += 1
        if self.failures >= self.max_failures:
            self._trip()

    def _record_success(self) -> None:
        self._trial_in_flight = False
        self.failures = 0
        self.state = "closed"

    def _trip(self) -> None:
        self.state = "open"
        self.opened_at = self._clock()
