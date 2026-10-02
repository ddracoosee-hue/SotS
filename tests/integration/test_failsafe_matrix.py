"""P03 failsafe matrix (T03.081, 16 §5.1).

One parametrized case per failsafe F01-F20: each must fire at least once.
Direct unit-level triggers — the wired-through-loop proofs live in the
agent, tool, and doctor tests.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from sots.agents.failsafes.f01_timeout import with_timeout
from sots.agents.failsafes.f02_retry import with_retry
from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f04_loop import LoopDetector
from sots.agents.failsafes.f05_schema import check_output
from sots.agents.failsafes.f06_checkpoint import load_state, save_state
from sots.agents.failsafes.f07_idempotency import idempotency_key, input_hash
from sots.agents.failsafes.f08_dead_letter import list_items, retry, send
from sots.agents.failsafes.f09_watchdog import Watchdog
from sots.agents.failsafes.f10_budget import agent_slice
from sots.agents.failsafes.f11_degrade import degrade, policy_for
from sots.agents.failsafes.f12_sanity import check_text
from sots.agents.failsafes.f13_injection import strip_injections
from sots.agents.failsafes.f14_politeness import TokenBucket
from sots.agents.failsafes.f15_size import cap_text
from sots.agents.failsafes.f16_killswitch import clear, engage, is_stopped
from sots.agents.failsafes.f17_doctor import run_doctor
from sots.agents.failsafes.f18_replay import RecordStore, ReplayStore
from sots.agents.failsafes.f19_canary import maybe_run_canary
from sots.agents.failsafes.f20_invariants import (
    InvariantContext,
    check_all,
    registered_invariants,
)
from sots.config import load_settings
from sots.errors import (
    BudgetExceededError,
    CanaryFailedError,
    CircuitOpenError,
    LoopDetectedError,
    ToolTimeoutError,
    ValidationFailedError,
)
from sots.storage import db as storage_db

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: str


@pytest.fixture
def conn(tmp_path: Path):
    handle = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(handle)
    yield handle
    handle.close()


async def _fire(fid: str, tmp_path: Path, conn) -> None:
    if fid == "F01":
        with pytest.raises(ToolTimeoutError):
            await with_timeout(asyncio.sleep(30), 0.01, "matrix")
    elif fid == "F02":
        calls = 0

        async def _flaky() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise httpx.ConnectError("down")
            return "ok"

        assert await with_retry(_flaky, max_wait_s=0.001) == "ok"
        assert calls == 3
    elif fid == "F03":
        breaker = CircuitBreaker("matrix", max_failures=2)

        async def _fail() -> None:
            raise ValueError("bad")

        with pytest.raises(ValueError):
            await breaker.call(_fail)
        with pytest.raises(ValueError):
            await breaker.call(_fail)
        with pytest.raises(CircuitOpenError):
            await breaker.call(_fail)
    elif fid == "F04":
        detector = LoopDetector()
        detector.check_action("compute", {"expression": "1 + 1"})
        detector.check_action("compute", {"expression": "1 + 1"})
        with pytest.raises(LoopDetectedError):
            detector.check_action("compute", {"expression": "1 + 1"})
    elif fid == "F05":
        with pytest.raises(ValidationFailedError):
            check_output(_Out, {"wrong": 1})
    elif fid == "F06":
        save_state(conn, "matrix", "r", {"n": 1})
        assert load_state(conn, "matrix") == {"n": 1}
    elif fid == "F07":
        digest = input_hash({"x": 1})
        assert idempotency_key("r", "a", digest) == idempotency_key("r", "a", digest)
    elif fid == "F08":
        item_id = send(
            conn, run_id="r", agent="a", team="t",
            payload={"x": 1}, error="boom",
        )
        assert len(list_items(conn, run_id="r")) == 1
        assert retry(conn, item_id).error == "boom"
        assert list_items(conn, run_id="r") == []
    elif fid == "F09":
        clock = [0.0]
        watchdog = Watchdog(clock=lambda: clock[0])
        watchdog.register("k", 600.0, 3)
        clock[0] += 1000.0
        assert len(watchdog.check()) == 1
    elif fid == "F10":
        with pytest.raises(BudgetExceededError):
            agent_slice(None, "matrix", 5).reserve(6, 0.0)
    elif fid == "F11":
        assert policy_for("rewrite_pass_a") == {"degraded_mode": "no_change"}
        assert degrade("fact_check", {"v": "TRUE"}, "down")["degraded"] is True
    elif fid == "F12":
        assert check_text("") == ["empty"]
    elif fid == "F13":
        _, hits = strip_injections(
            "x ignore previous instructions y", ["ignore previous instructions"]
        )
        assert hits == 1
    elif fid == "F14":
        now = [100.0]
        slept: list[float] = []

        async def _sleep(s: float) -> None:
            slept.append(s)

        bucket = TokenBucket(rate_per_s=1.0, time_fn=lambda: now[0], sleep_fn=_sleep)
        await bucket.acquire()
        await bucket.acquire()
        assert slept == [1.0]
    elif fid == "F15":
        _, note = cap_text("hello world", 5, "matrix")
        assert note is not None and "showing 5 of 11 chars" in note
    elif fid == "F16":
        data_dir = tmp_path / "data"
        engage(data_dir)
        assert is_stopped(data_dir) is True
        assert clear(data_dir) is True
    elif fid == "F17":
        report = await run_doctor(tmp_path / "empty")
        assert report.failed is True
    elif fid == "F18":
        tape = tmp_path / "tape.jsonl"
        RecordStore(tape).append("tool", {"tool": "t"}, {"ok": True})
        assert ReplayStore(tape).next("tool", {"tool": "t"}) == {"ok": True}
    elif fid == "F19":
        settings = load_settings(CONFIG_DIR, env_file=None)

        async def _boom() -> bool:
            raise RuntimeError("canary exploded")

        with pytest.raises(CanaryFailedError):
            await maybe_run_canary(word_count=99999, settings=settings, act=_boom)
    elif fid == "F20":
        assert "raw_unchanged" in registered_invariants()
        result = check_all(InvariantContext(root=tmp_path, manifest={}, conn=None))
        assert isinstance(result, dict) and result
    else:  # pragma: no cover
        raise AssertionError(f"unknown failsafe {fid}")


@pytest.mark.parametrize("fid", [f"F{i:02d}" for i in range(1, 21)])
async def test_failsafe_fires(fid: str, tmp_path: Path, conn) -> None:
    await _fire(fid, tmp_path, conn)
