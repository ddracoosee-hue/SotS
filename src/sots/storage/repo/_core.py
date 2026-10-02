"""Shared persistence machinery for storage/repo (W0 split of repo.py)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


def to_json(value: Any) -> str:
    """Serialize a list/dict/nested value for a JSON TEXT column."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def from_json(text: str) -> Any:
    """Parse a JSON TEXT column back to Python data."""
    return json.loads(text)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass(frozen=True)
class _Spec:
    table: str
    model: type[BaseModel]
    pk: tuple[str, ...]  # model fields forming the PK; () = surrogate AUTOINCREMENT id
    json_fields: frozenset[str] = frozenset()

    @property
    def columns(self) -> list[str]:
        cols = list(self.model.model_fields)
        if not self.pk:
            cols = ["id", *cols]
        return cols

def _dump_row(spec: _Spec, model: BaseModel) -> dict[str, Any]:
    dumped = model.model_dump(mode="json")
    row: dict[str, Any] = {}
    for fname in spec.model.model_fields:
        value = dumped[fname]
        if fname in spec.json_fields and value is not None:
            value = to_json(value)
        row[fname] = value
    return row


def _load_row(spec: _Spec, row: Any) -> BaseModel:
    data = dict(row)
    fields = spec.model.model_fields
    kwargs: dict[str, Any] = {}
    for fname in fields:
        value = data.get(fname)
        if fname in spec.json_fields and value is not None:
            value = from_json(value)
        kwargs[fname] = value
    return spec.model(**kwargs)


def _save(conn: sqlite3.Connection, spec: _Spec, model: BaseModel) -> Any:
    row = _dump_row(spec, model)
    cols = list(row)
    placeholders = ", ".join("?" for _ in cols)
    sql = (
        f"INSERT OR REPLACE INTO {_q(spec.table)}"
        f" ({', '.join(_q(c) for c in cols)}) VALUES ({placeholders})"
    )
    with conn:
        cur = conn.execute(sql, [row[c] for c in cols])
    if spec.pk:
        keys = tuple(getattr(model, k) for k in spec.pk)
        return keys[0] if len(keys) == 1 else keys
    return cur.lastrowid


def _get(conn: sqlite3.Connection, spec: _Spec, key: Any) -> BaseModel | None:
    if not spec.pk:
        sql = f"SELECT * FROM {_q(spec.table)} WHERE {_q('id')} = ?"
        params: tuple[Any, ...] = (key,)
    else:
        keys = key if isinstance(key, tuple) else (key,)
        where = " AND ".join(f"{_q(c)} = ?" for c in spec.pk)
        sql = f"SELECT * FROM {_q(spec.table)} WHERE {where}"
        params = keys
    row = conn.execute(sql, params).fetchone()
    return _load_row(spec, row) if row is not None else None


def _list(
    conn: sqlite3.Connection, spec: _Spec, *, limit: int | None = None, **filters: Any
) -> list[BaseModel]:
    known = set(spec.columns)
    clauses: list[str] = []
    params: list[Any] = []
    for name, value in filters.items():
        if name not in known:
            raise ValueError(f"unknown filter {name!r} for table {spec.table}")
        if value is None:
            continue
        clauses.append(f"{_q(name)} = ?")
        params.append(value)
    sql = f"SELECT * FROM {_q(spec.table)}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return [_load_row(spec, row) for row in conn.execute(sql, params)]


def _delete(conn: sqlite3.Connection, spec: _Spec, key: Any) -> bool:
    if not spec.pk:
        sql = f"DELETE FROM {_q(spec.table)} WHERE {_q('id')} = ?"
        params: tuple[Any, ...] = (key,)
    else:
        keys = key if isinstance(key, tuple) else (key,)
        where = " AND ".join(f"{_q(c)} = ?" for c in spec.pk)
        sql = f"DELETE FROM {_q(spec.table)} WHERE {where}"
        params = keys
    with conn:
        cur = conn.execute(sql, params)
    return cur.rowcount > 0

