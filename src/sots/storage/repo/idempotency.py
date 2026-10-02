"""idempotency persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from sots.storage.repo._core import _q, _save, _utcnow
from sots.storage.repo._specs import (
    _BY_MODEL,
    _SPECS,
)


def idempotent_save(conn: sqlite3.Connection, model: BaseModel, key: str) -> bool:
    """Insert-or-ignore on an idempotency key; True when the row was written.

    The first call with a given key persists `model`; later calls with the
    same key leave the stored row untouched and return False.
    """
    try:
        spec = _BY_MODEL[type(model)]
    except KeyError as exc:
        raise ValueError(f"no table registered for {type(model).__name__}") from exc
    with conn:
        cur = conn.execute(
            'INSERT OR IGNORE INTO "idempotency_keys" ("key", "created_at")'
            " VALUES (?, ?)",
            (key, _utcnow()),
        )
        if cur.rowcount == 0:
            return False
    _save(conn, spec, model)
    return True


_RUN_COUNT_TABLES: tuple[str, ...] = tuple(
    sorted(
        {s.table for s in _SPECS if "run_id" in s.model.model_fields}
        | {"summaries", "dead_letters", "checkpoints", "events", "dialogues", "waivers"}
    )
)


def snapshot_counts(conn: sqlite3.Connection, run_id: str) -> dict[str, int]:
    """Per-table row counts for one run, for invariant checks (F20)."""
    counts: dict[str, int] = {}
    for table in _RUN_COUNT_TABLES:
        row = conn.execute(
            f'SELECT COUNT(*) AS n FROM {_q(table)} WHERE "run_id" = ?', (run_id,)
        ).fetchone()
        counts[table] = int(row["n"])
    return counts
