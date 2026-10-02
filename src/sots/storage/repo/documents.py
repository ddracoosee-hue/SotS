"""documents persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.document import (
    Chunk,
    Document,
)
from sots.models.unit import Unit
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _CHUNKS,
    _DOCUMENTS,
    _UNITS,
)


def save_document(conn: sqlite3.Connection, doc: Document) -> str:
    return cast(str, _save(conn, _DOCUMENTS, doc))


def get_document(conn: sqlite3.Connection, doc_id: str) -> Document | None:
    return cast(Document | None, _get(conn, _DOCUMENTS, doc_id))


def list_documents(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Document]:
    return cast(list[Document], _list(conn, _DOCUMENTS, limit=limit, **filters))


def save_chunk(conn: sqlite3.Connection, chunk: Chunk) -> str:
    return cast(str, _save(conn, _CHUNKS, chunk))


def get_chunk(conn: sqlite3.Connection, chunk_id: str) -> Chunk | None:
    return cast(Chunk | None, _get(conn, _CHUNKS, chunk_id))


def list_chunks(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Chunk]:
    return cast(list[Chunk], _list(conn, _CHUNKS, limit=limit, **filters))


def save_unit(conn: sqlite3.Connection, unit: Unit) -> str:
    return cast(str, _save(conn, _UNITS, unit))


def get_unit(conn: sqlite3.Connection, unit_id: str) -> Unit | None:
    return cast(Unit | None, _get(conn, _UNITS, unit_id))


def list_units(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Unit]:
    return cast(list[Unit], _list(conn, _UNITS, limit=limit, **filters))


