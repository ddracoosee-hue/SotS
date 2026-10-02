"""legal_learning persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.learning import (
    LearningChange,
    PromptTrial,
)
from sots.models.legal import (
    DefenseMemo,
    LegalIssue,
    Position,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _DEFENSE_MEMOS,
    _LEARNING_CHANGES,
    _LEGAL_ISSUES,
    _POSITIONS,
    _PROMPT_TRIALS,
)


def save_legal_issue(conn: sqlite3.Connection, issue: LegalIssue) -> str:
    return cast(str, _save(conn, _LEGAL_ISSUES, issue))


def get_legal_issue(conn: sqlite3.Connection, issue_id: str) -> LegalIssue | None:
    return cast(LegalIssue | None, _get(conn, _LEGAL_ISSUES, issue_id))


def list_legal_issues(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LegalIssue]:
    return cast(list[LegalIssue], _list(conn, _LEGAL_ISSUES, limit=limit, **filters))


def save_position(conn: sqlite3.Connection, position: Position) -> str:
    return cast(str, _save(conn, _POSITIONS, position))


def get_position(conn: sqlite3.Connection, position_id: str) -> Position | None:
    return cast(Position | None, _get(conn, _POSITIONS, position_id))


def list_positions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Position]:
    return cast(list[Position], _list(conn, _POSITIONS, limit=limit, **filters))


def save_defense_memo(conn: sqlite3.Connection, memo: DefenseMemo) -> str:
    return cast(str, _save(conn, _DEFENSE_MEMOS, memo))


def get_defense_memo(conn: sqlite3.Connection, memo_id: str) -> DefenseMemo | None:
    return cast(DefenseMemo | None, _get(conn, _DEFENSE_MEMOS, memo_id))


def list_defense_memos(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DefenseMemo]:
    return cast(list[DefenseMemo], _list(conn, _DEFENSE_MEMOS, limit=limit, **filters))


def save_learning_change(conn: sqlite3.Connection, change: LearningChange) -> str:
    return cast(str, _save(conn, _LEARNING_CHANGES, change))


def get_learning_change(conn: sqlite3.Connection, change_id: str) -> LearningChange | None:
    return cast(LearningChange | None, _get(conn, _LEARNING_CHANGES, change_id))


def list_learning_changes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LearningChange]:
    return cast(
        list[LearningChange], _list(conn, _LEARNING_CHANGES, limit=limit, **filters)
    )


def save_prompt_trial(conn: sqlite3.Connection, trial: PromptTrial) -> str:
    return cast(str, _save(conn, _PROMPT_TRIALS, trial))


def get_prompt_trial(conn: sqlite3.Connection, trial_id: str) -> PromptTrial | None:
    return cast(PromptTrial | None, _get(conn, _PROMPT_TRIALS, trial_id))


def list_prompt_trials(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PromptTrial]:
    return cast(list[PromptTrial], _list(conn, _PROMPT_TRIALS, limit=limit, **filters))


