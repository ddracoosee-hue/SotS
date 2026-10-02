"""Agent event bus: async pub/sub + JSONL sink (P03 T03.070, 16 §7).

The runtime emits lifecycle events here; the TUI subscribes, and every event
is appended to `data/logs/events.jsonl` when a log path is configured.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sots.errors import ConfigError

#: Event types from 16 §7 (nothing else may be emitted).
EVENT_TYPES = frozenset(
    {
        "agent.start",
        "agent.step",
        "agent.tool",
        "agent.grade",
        "agent.done",
        "agent.failed",
        "gate.pass",
        "gate.fail",
        "act.start",
        "act.done",
        "author.input_needed",
    }
)


class Event(BaseModel):
    """One bus event (frozen; JSONL-serializable)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str
    run_id: str | None = None
    agent: str | None = None
    payload: dict[str, Any] = {}
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    """In-process fan-out; optionally appends every event to a JSONL log."""

    def __init__(self, *, log_path: str | Path | None = None) -> None:
        self._log_path = Path(log_path) if log_path is not None else None
        self._queues: list[tuple[str | None, asyncio.Queue[Event]]] = []

    def subscribe(self, event_type: str | None = None) -> asyncio.Queue[Event]:
        """A queue receiving future events (all types, or one when given)."""
        if event_type is not None and event_type not in EVENT_TYPES:
            raise ConfigError(f"unknown event type {event_type!r}")
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues.append((event_type, queue))
        return queue

    async def emit(
        self,
        event_type: str,
        *,
        run_id: str | None = None,
        agent: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        """Validate, sink, and fan out one event (in order, per subscriber)."""
        if event_type not in EVENT_TYPES:
            raise ConfigError(f"unknown event type {event_type!r}")
        event = Event(
            type=event_type, run_id=run_id, agent=agent, payload=payload or {}
        )
        if self._log_path is not None:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(event.model_dump_json() + "\n")
        for wanted, queue in self._queues:
            if wanted is None or wanted == event_type:
                queue.put_nowait(event)
        return event

    def subscriber_count(self) -> int:
        """How many queues are subscribed (tests/diagnostics)."""
        return len(self._queues)


async def emit_optional(
    bus: EventBus | None,
    event_type: str,
    *,
    run_id: str | None = None,
    agent: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Emit when a bus is wired; the loop never depends on observers."""
    if bus is not None:
        await bus.emit(
            event_type, run_id=run_id, agent=agent, payload=payload or {}
        )


def default_log_path(data_dir: str | Path) -> Path:
    """The 16 §7 sink: `data/logs/events.jsonl` under the data dir."""
    return Path(data_dir) / "logs" / "events.jsonl"


def read_log(log_path: str | Path) -> list[Event]:
    """Read back a JSONL event log (tests/replay tooling)."""
    path = Path(log_path)
    if not path.is_file():
        return []
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(Event.model_validate(json.loads(line)))
    return events
