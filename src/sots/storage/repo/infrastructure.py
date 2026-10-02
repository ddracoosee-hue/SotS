"""infrastructure persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any

from sots.storage.repo._core import _q, _utcnow, from_json, to_json

_SUMMARY_COLS = ("id", "run_id", "kind", "unit_id", "document_id", "chapter_id", "status")


def save_summary(
    conn: sqlite3.Connection,
    summary_id: str,
    kind: str,
    body: dict[str, Any],
    *,
    run_id: str | None = None,
    unit_id: str | None = None,
    document_id: str | None = None,
    chapter_id: str | None = None,
    status: str | None = None,
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "summaries" ("id", "run_id", "kind", "unit_id",'
            ' "document_id", "chapter_id", "status", "body", "created_at")'
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                summary_id, run_id, kind, unit_id, document_id, chapter_id,
                status, to_json(body), _utcnow(),
            ),
        )
    return summary_id


def get_summary(conn: sqlite3.Connection, summary_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "summaries" WHERE "id" = ?', (summary_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["body"] = from_json(data["body"])
    return data


def list_summaries(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for name, value in filters.items():
        if name not in _SUMMARY_COLS:
            raise ValueError(f"unknown summaries filter {name!r}")
        if value is None:
            continue
        clauses.append(f"{_q(name)} = ?")
        params.append(value)
    sql = 'SELECT * FROM "summaries"'
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["body"] = from_json(data["body"])
        out.append(data)
    return out


def cache_set(
    conn: sqlite3.Connection, key: str, value: str, *, expires_at: str | None = None
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "cache" ("key", "value", "created_at", "expires_at")'
            " VALUES (?, ?, ?, ?)",
            (key, value, _utcnow(), expires_at),
        )
    return key


def cache_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute('SELECT "value" FROM "cache" WHERE "key" = ?', (key,)).fetchone()
    return str(row["value"]) if row is not None else None


def cache_delete(conn: sqlite3.Connection, key: str) -> bool:
    with conn:
        cur = conn.execute('DELETE FROM "cache" WHERE "key" = ?', (key,))
    return cur.rowcount > 0


def save_dead_letter(
    conn: sqlite3.Connection,
    agent: str,
    team: str,
    payload: dict[str, Any],
    error: str,
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "dead_letters" ("run_id", "agent", "team", "payload", "error",'
            ' "created_at") VALUES (?, ?, ?, ?, ?, ?)',
            (run_id, agent, team, to_json(payload), error, _utcnow()),
        )
    return int(cur.lastrowid or 0)


def get_dead_letter(conn: sqlite3.Connection, item_id: int) -> dict[str, Any] | None:
    row = conn.execute('SELECT * FROM "dead_letters" WHERE "id" = ?', (item_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["payload"] = from_json(data["payload"])
    return data


def delete_dead_letter(conn: sqlite3.Connection, item_id: int) -> bool:
    with conn:
        cur = conn.execute('DELETE FROM "dead_letters" WHERE "id" = ?', (item_id,))
    return cur.rowcount > 0


def list_dead_letters(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "dead_letters"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["payload"] = from_json(data["payload"])
        out.append(data)
    return out


def save_checkpoint(
    conn: sqlite3.Connection, key: str, state: dict[str, Any], *, run_id: str | None = None
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "checkpoints" ("key", "run_id", "state", "updated_at")'
            " VALUES (?, ?, ?, ?)",
            (key, run_id, to_json(state), _utcnow()),
        )
    return key


def get_checkpoint(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "checkpoints" WHERE "key" = ?', (key,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["state"] = from_json(data["state"])
    return data


def delete_checkpoint(conn: sqlite3.Connection, key: str) -> bool:
    """Drop a checkpoint (terminal runs leave nothing to resume)."""
    with conn:
        cur = conn.execute('DELETE FROM "checkpoints" WHERE "key" = ?', (key,))
    return cur.rowcount > 0


def append_event(
    conn: sqlite3.Connection,
    event_type: str,
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "events" ("run_id", "type", "payload", "created_at")'
            " VALUES (?, ?, ?, ?)",
            (run_id, event_type, to_json(payload), _utcnow()),
        )
    return int(cur.lastrowid or 0)


def list_events(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "events"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["payload"] = from_json(data["payload"])
        out.append(data)
    return out


def save_dialogue(
    conn: sqlite3.Connection,
    dialogue_id: str,
    turns: list[dict[str, Any]],
    status: str,
    *,
    run_id: str | None = None,
    proposal_id: str | None = None,
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "dialogues" ("id", "run_id", "proposal_id", "turns",'
            ' "status", "updated_at") VALUES (?, ?, ?, ?, ?, ?)',
            (dialogue_id, run_id, proposal_id, to_json(turns), status, _utcnow()),
        )
    return dialogue_id


def get_dialogue(conn: sqlite3.Connection, dialogue_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "dialogues" WHERE "id" = ?', (dialogue_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["turns"] = from_json(data["turns"])
    return data


def save_waiver(
    conn: sqlite3.Connection,
    issue_id: str,
    reason: str,
    decided_by: str,
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "waivers" ("run_id", "issue_id", "reason", "decided_by",'
            ' "decided_at") VALUES (?, ?, ?, ?, ?)',
            (run_id, issue_id, reason, decided_by, _utcnow()),
        )
    return int(cur.lastrowid or 0)


def list_waivers(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "waivers"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return [dict(row) for row in conn.execute(sql, params)]


