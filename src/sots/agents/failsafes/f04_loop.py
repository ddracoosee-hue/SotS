"""F04 loop detection (P03 T03.043, 16 §5.1).

Raises LoopDetectedError when the agent repeats the same (tool, args) 3
times, or when 2 consecutive observations hash identically (no new
information). The runtime answers with a forced degraded final.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sots.errors import LoopDetectedError

MAX_SAME_ACTION = 3
MAX_UNCHANGED_OBS = 2


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


class LoopDetector:
    """Per-invocation loop state (snapshotted into checkpoints)."""

    def __init__(self) -> None:
        self.action_counts: dict[str, int] = {}
        self.last_obs_hash: str | None = None
        self.unchanged_streak = 0

    def check_action(self, tool: str, args: dict[str, Any] | None) -> None:
        """Count a (tool, args) pair; the 3rd repeat raises."""
        key = _stable_hash({"tool": tool, "args": args or {}})
        count = self.action_counts.get(key, 0) + 1
        self.action_counts[key] = count
        if count >= MAX_SAME_ACTION:
            raise LoopDetectedError(f"tool {tool!r} repeated with identical args 3 times")

    def check_observation(self, content: str) -> None:
        """Track information gain; 2 identical hashes in a row raises."""
        digest = _stable_hash(content)
        if digest == self.last_obs_hash:
            self.unchanged_streak += 1
        else:
            self.last_obs_hash = digest
            self.unchanged_streak = 1
        if self.unchanged_streak >= MAX_UNCHANGED_OBS:
            raise LoopDetectedError("2 consecutive observations with no new information")

    def snapshot(self) -> dict[str, Any]:
        """JSON-able state for checkpoints."""
        return {
            "action_counts": dict(self.action_counts),
            "last_obs_hash": self.last_obs_hash,
            "unchanged_streak": self.unchanged_streak,
        }

    def restore(self, snapshot: dict[str, Any]) -> None:
        """Restore checkpointed state (missing keys default to fresh)."""
        self.action_counts = dict(snapshot.get("action_counts", {}))
        self.last_obs_hash = snapshot.get("last_obs_hash")
        self.unchanged_streak = int(snapshot.get("unchanged_streak", 0))
