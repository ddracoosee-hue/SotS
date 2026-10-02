"""Checkpoint persistence and run usage sums (W0 split of agents/base.py)."""

from __future__ import annotations

import logging
from typing import Any

from sots.agents.failsafes.f04_loop import LoopDetector
from sots.agents.failsafes.f06_checkpoint import load_state, save_state
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

logger = logging.getLogger(__name__)


def save_checkpoint(
    conn: Connection,
    checkpoint_key: str,
    run_id: str,
    entries: list[dict[str, Any]],
    step: int,
    loop: LoopDetector,
    invalid_streak: int,
) -> None:
    """F06 save after every step (kill + resume continue from here)."""
    save_state(
        conn, checkpoint_key, run_id,
        {
            "version": 1,
            "scratchpad": entries,
            "step": step,
            "loop": loop.snapshot(),
            "invalid_streak": invalid_streak,
        },
    )


def restore_checkpoint(
    conn: Connection, checkpoint_key: str
) -> tuple[list[dict[str, Any]], int, LoopDetector, int]:
    """F06 resume; corrupt checkpoints restart from scratch (T03.045)."""
    entries: list[dict[str, Any]] = []
    loop = LoopDetector()
    try:
        state = load_state(conn, checkpoint_key)
    except Exception as exc:
        logger.warning("checkpoint %r corrupt, restarting: %s", checkpoint_key, exc)
        return [], 0, loop, 0
    if state is None:
        return [], 0, loop, 0
    raw_entries = state.get("scratchpad", [])
    if isinstance(raw_entries, list):
        entries = [e for e in raw_entries if isinstance(e, dict)]
    step = state.get("step", 0)
    step = step if isinstance(step, int) and step >= 0 else 0
    raw_loop = state.get("loop", {})
    if isinstance(raw_loop, dict):
        loop.restore(raw_loop)
    streak = state.get("invalid_streak", 0)
    streak = streak if isinstance(streak, int) and streak >= 0 else 0
    return entries, step, loop, streak


def run_usage(conn: Connection, run_id: str) -> tuple[int, int, float]:
    """Sum this run's LLM calls from the call log (T03.013)."""
    calls = storage_repo.list_llm_calls(conn, run_id=run_id)
    return (
        sum(call.input_tokens for call in calls),
        sum(call.output_tokens for call in calls),
        sum(call.cost_estimate for call in calls),
    )
