"""media_psyche persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.media import (
    MediaCheck,
    MediaWork,
)
from sots.models.psyche import (
    EngineFinding,
    Synthesis,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _ENGINE_FINDINGS,
    _MEDIA_CHECKS,
    _MEDIA_WORKS,
    _SYNTHESES,
)


def save_media_work(conn: sqlite3.Connection, work: MediaWork) -> str:
    return cast(str, _save(conn, _MEDIA_WORKS, work))


def get_media_work(conn: sqlite3.Connection, work_id: str) -> MediaWork | None:
    return cast(MediaWork | None, _get(conn, _MEDIA_WORKS, work_id))


def list_media_works(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MediaWork]:
    return cast(list[MediaWork], _list(conn, _MEDIA_WORKS, limit=limit, **filters))


def save_media_check(conn: sqlite3.Connection, check: MediaCheck) -> str:
    return cast(str, _save(conn, _MEDIA_CHECKS, check))


def get_media_check(conn: sqlite3.Connection, check_id: str) -> MediaCheck | None:
    return cast(MediaCheck | None, _get(conn, _MEDIA_CHECKS, check_id))


def list_media_checks(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MediaCheck]:
    return cast(list[MediaCheck], _list(conn, _MEDIA_CHECKS, limit=limit, **filters))


def save_engine_finding(conn: sqlite3.Connection, finding: EngineFinding) -> str:
    return cast(str, _save(conn, _ENGINE_FINDINGS, finding))


def get_engine_finding(conn: sqlite3.Connection, finding_id: str) -> EngineFinding | None:
    return cast(EngineFinding | None, _get(conn, _ENGINE_FINDINGS, finding_id))


def list_engine_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[EngineFinding]:
    return cast(
        list[EngineFinding], _list(conn, _ENGINE_FINDINGS, limit=limit, **filters)
    )


def save_synthesis(conn: sqlite3.Connection, synthesis: Synthesis) -> str:
    return cast(str, _save(conn, _SYNTHESES, synthesis))


def get_synthesis(conn: sqlite3.Connection, run_id: str) -> Synthesis | None:
    return cast(Synthesis | None, _get(conn, _SYNTHESES, run_id))


def list_syntheses(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Synthesis]:
    return cast(list[Synthesis], _list(conn, _SYNTHESES, limit=limit, **filters))


