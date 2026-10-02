"""F09 watchdog: heartbeats, stall detection, requeue policy (P03 T03.048, 16 §5.1).

Agents heartbeat every step. No heartbeat for `max(60, 2 * timeout_s /
max_steps)` seconds means a stall: the first stall requeues once, the second
sends the agent to the dead-letter queue. `check()` returns actions; the
orchestrator performs them. The clock is injectable for tests.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import NamedTuple

MIN_INTERVAL_S = 60.0


class WatchdogAction(NamedTuple):
    """One watchdog decision: ("requeue"|"dead_letter", key)."""

    action: str
    key: str


class _Tracked:
    def __init__(self, interval_s: float, now: float) -> None:
        self.interval_s = interval_s
        self.last_heartbeat = now
        self.stalls = 0


class Watchdog:
    """Heartbeat registry + stall monitor (one per orchestrator)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._tracked: dict[str, _Tracked] = {}

    @staticmethod
    def interval_for(timeout_s: float, max_steps: int) -> float:
        """Stall interval: 2 x timeout/max_steps, minimum 60 s (16 §5.1)."""
        return max(MIN_INTERVAL_S, 2 * timeout_s / max(1, max_steps))

    def register(self, key: str, timeout_s: float, max_steps: int) -> None:
        """Track an agent invocation (heartbeats start now)."""
        self._tracked[key] = _Tracked(self.interval_for(timeout_s, max_steps), self._clock())

    def heartbeat(self, key: str) -> None:
        """Record a step heartbeat (unknown keys are ignored)."""
        tracked = self._tracked.get(key)
        if tracked is not None:
            tracked.last_heartbeat = self._clock()

    def unregister(self, key: str) -> None:
        """Stop tracking a finished agent."""
        self._tracked.pop(key, None)

    def check(self) -> list[WatchdogAction]:
        """Stall decisions: requeue once, dead letter on the second stall."""
        now = self._clock()
        actions: list[WatchdogAction] = []
        for key, tracked in list(self._tracked.items()):
            if now - tracked.last_heartbeat <= tracked.interval_s:
                continue
            tracked.stalls += 1
            if tracked.stalls == 1:
                tracked.last_heartbeat = now  # one more full window
                actions.append(WatchdogAction("requeue", key))
            else:
                del self._tracked[key]
                actions.append(WatchdogAction("dead_letter", key))
        return actions
