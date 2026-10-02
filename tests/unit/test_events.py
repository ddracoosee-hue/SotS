"""P03 event bus tests (T03.070, 16 §7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sots.agents.events import EventBus, default_log_path, read_log
from sots.errors import ConfigError


async def test_subscribe_receives_in_order() -> None:
    bus = EventBus()
    queue = bus.subscribe()
    assert bus.subscriber_count() == 1
    await bus.emit("agent.start", run_id="r", agent="a")
    await bus.emit("agent.step", run_id="r", agent="a", payload={"step": 1})
    await bus.emit("agent.done", run_id="r", agent="a")
    received = [queue.get_nowait() for _ in range(3)]
    assert [event.type for event in received] == [
        "agent.start", "agent.step", "agent.done",
    ]
    assert received[1].payload == {"step": 1}
    assert received[0].run_id == "r" and received[0].agent == "a"
    assert queue.empty()


async def test_filtered_subscription() -> None:
    bus = EventBus()
    done_only = bus.subscribe("agent.done")
    everything = bus.subscribe()
    await bus.emit("agent.step", run_id="r", agent="a")
    await bus.emit("agent.done", run_id="r", agent="a")
    assert done_only.qsize() == 1
    assert (await done_only.get()).type == "agent.done"
    assert everything.qsize() == 2


async def test_unknown_event_type_rejected() -> None:
    bus = EventBus()
    with pytest.raises(ConfigError, match="unknown event type"):
        await bus.emit("nope.happened", run_id="r", agent="a")
    with pytest.raises(ConfigError, match="unknown event type"):
        bus.subscribe("nope.happened")


async def test_jsonl_sink_roundtrip(tmp_path: Path) -> None:
    log_path = default_log_path(tmp_path / "data")
    assert log_path == tmp_path / "data" / "logs" / "events.jsonl"
    assert read_log(log_path) == []
    bus = EventBus(log_path=log_path)
    await bus.emit("act.start", run_id="r", agent="a", payload={"act": "I"})
    await bus.emit("act.done", run_id="r", agent="a")
    events = read_log(log_path)
    assert [event.type for event in events] == ["act.start", "act.done"]
    assert events[0].payload == {"act": "I"}
    assert events[0].at <= events[1].at
