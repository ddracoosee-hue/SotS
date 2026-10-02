"""agents_grading persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.agents import (
    AgentCard,
    AgentRun,
    BudgetSlice,
)
from sots.models.grading import (
    GradeRecord,
    GraderHealth,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _AGENT_CARDS,
    _AGENT_RUNS,
    _BUDGET_SLICES,
    _GRADE_RECORDS,
    _GRADER_HEALTH,
)


def save_agent_card(conn: sqlite3.Connection, card: AgentCard) -> str:
    return cast(str, _save(conn, _AGENT_CARDS, card))


def get_agent_card(conn: sqlite3.Connection, name: str) -> AgentCard | None:
    return cast(AgentCard | None, _get(conn, _AGENT_CARDS, name))


def list_agent_cards(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AgentCard]:
    return cast(list[AgentCard], _list(conn, _AGENT_CARDS, limit=limit, **filters))


def save_agent_run(conn: sqlite3.Connection, run: AgentRun) -> str:
    return cast(str, _save(conn, _AGENT_RUNS, run))


def get_agent_run(conn: sqlite3.Connection, run_id: str) -> AgentRun | None:
    return cast(AgentRun | None, _get(conn, _AGENT_RUNS, run_id))


def list_agent_runs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AgentRun]:
    return cast(list[AgentRun], _list(conn, _AGENT_RUNS, limit=limit, **filters))


def save_budget_slice(conn: sqlite3.Connection, budget_slice: BudgetSlice) -> str:
    return cast(str, _save(conn, _BUDGET_SLICES, budget_slice))


def get_budget_slice(conn: sqlite3.Connection, scope: str) -> BudgetSlice | None:
    return cast(BudgetSlice | None, _get(conn, _BUDGET_SLICES, scope))


def list_budget_slices(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[BudgetSlice]:
    return cast(list[BudgetSlice], _list(conn, _BUDGET_SLICES, limit=limit, **filters))


def save_grade_record(conn: sqlite3.Connection, record: GradeRecord) -> str:
    return cast(str, _save(conn, _GRADE_RECORDS, record))


def get_grade_record(conn: sqlite3.Connection, record_id: str) -> GradeRecord | None:
    return cast(GradeRecord | None, _get(conn, _GRADE_RECORDS, record_id))


def list_grade_records(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[GradeRecord]:
    return cast(list[GradeRecord], _list(conn, _GRADE_RECORDS, limit=limit, **filters))


def save_grader_health(conn: sqlite3.Connection, health: GraderHealth) -> int:
    return cast(int, _save(conn, _GRADER_HEALTH, health))


def get_grader_health(conn: sqlite3.Connection, health_id: int) -> GraderHealth | None:
    return cast(GraderHealth | None, _get(conn, _GRADER_HEALTH, health_id))


def list_grader_health(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[GraderHealth]:
    return cast(list[GraderHealth], _list(conn, _GRADER_HEALTH, limit=limit, **filters))


