"""profile_runs persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.cache import CacheEntry
from sots.models.profile import (
    AuthorProfile,
    BookProfile,
    ChapterBrief,
)
from sots.models.run import (
    ChapterState,
    LLMCall,
    Run,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _AUTHOR_PROFILES,
    _BOOK_PROFILES,
    _CACHE,
    _CHAPTER_BRIEFS,
    _CHAPTER_STATE,
    _LLM_CALLS,
    _RUNS,
)


def save_author_profile(conn: sqlite3.Connection, profile: AuthorProfile) -> int:
    return cast(int, _save(conn, _AUTHOR_PROFILES, profile))


def get_author_profile(conn: sqlite3.Connection, profile_id: int) -> AuthorProfile | None:
    return cast(AuthorProfile | None, _get(conn, _AUTHOR_PROFILES, profile_id))


def list_author_profiles(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AuthorProfile]:
    return cast(
        list[AuthorProfile], _list(conn, _AUTHOR_PROFILES, limit=limit, **filters)
    )


def save_book_profile(conn: sqlite3.Connection, profile: BookProfile) -> int:
    return cast(int, _save(conn, _BOOK_PROFILES, profile))


def get_book_profile(conn: sqlite3.Connection, profile_id: int) -> BookProfile | None:
    return cast(BookProfile | None, _get(conn, _BOOK_PROFILES, profile_id))


def list_book_profiles(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[BookProfile]:
    return cast(list[BookProfile], _list(conn, _BOOK_PROFILES, limit=limit, **filters))


def save_chapter_brief(conn: sqlite3.Connection, brief: ChapterBrief) -> str:
    return cast(str, _save(conn, _CHAPTER_BRIEFS, brief))


def get_chapter_brief(conn: sqlite3.Connection, chapter_id: str) -> ChapterBrief | None:
    return cast(ChapterBrief | None, _get(conn, _CHAPTER_BRIEFS, chapter_id))


def list_chapter_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ChapterBrief]:
    return cast(
        list[ChapterBrief], _list(conn, _CHAPTER_BRIEFS, limit=limit, **filters)
    )


def save_run(conn: sqlite3.Connection, run: Run) -> str:
    return cast(str, _save(conn, _RUNS, run))


def get_run(conn: sqlite3.Connection, run_id: str) -> Run | None:
    return cast(Run | None, _get(conn, _RUNS, run_id))


def list_runs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Run]:
    return cast(list[Run], _list(conn, _RUNS, limit=limit, **filters))


def save_llm_call(conn: sqlite3.Connection, call: LLMCall) -> str:
    return cast(str, _save(conn, _LLM_CALLS, call))


def get_llm_call(conn: sqlite3.Connection, call_id: str) -> LLMCall | None:
    return cast(LLMCall | None, _get(conn, _LLM_CALLS, call_id))


def list_llm_calls(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LLMCall]:
    return cast(list[LLMCall], _list(conn, _LLM_CALLS, limit=limit, **filters))


def save_cache_entry(conn: sqlite3.Connection, entry: CacheEntry) -> str:
    return cast(str, _save(conn, _CACHE, entry))


def get_cache_entry(conn: sqlite3.Connection, key: str) -> CacheEntry | None:
    return cast(CacheEntry | None, _get(conn, _CACHE, key))


def count_cache_entries(conn: sqlite3.Connection) -> int:
    row = conn.execute('SELECT COUNT(*) AS n FROM "cache"').fetchone()
    return int(row["n"])


def save_chapter_state(conn: sqlite3.Connection, state: ChapterState) -> str:
    return cast(str, _save(conn, _CHAPTER_STATE, state))


def get_chapter_state(conn: sqlite3.Connection, chapter_id: str) -> ChapterState | None:
    return cast(ChapterState | None, _get(conn, _CHAPTER_STATE, chapter_id))


def list_chapter_states(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ChapterState]:
    return cast(
        list[ChapterState], _list(conn, _CHAPTER_STATE, limit=limit, **filters)
    )


