"""audience persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.audience import (
    AudienceBrief,
    AudienceScorecard,
    CalibrationRecord,
    MechanicsFinding,
    Persona,
    PersonaReaction,
    PlaybookEntry,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _AUDIENCE_BRIEFS,
    _CALIBRATION,
    _MECHANICS_FINDINGS,
    _PERSONA_REACTIONS,
    _PERSONAS,
    _PLAYBOOK,
    _SCORECARDS,
)


def save_persona(conn: sqlite3.Connection, persona: Persona) -> str:
    return cast(str, _save(conn, _PERSONAS, persona))


def get_persona(conn: sqlite3.Connection, persona_id: str) -> Persona | None:
    return cast(Persona | None, _get(conn, _PERSONAS, persona_id))


def list_personas(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Persona]:
    return cast(list[Persona], _list(conn, _PERSONAS, limit=limit, **filters))


def save_mechanics_finding(
    conn: sqlite3.Connection, finding: MechanicsFinding
) -> str:
    return cast(str, _save(conn, _MECHANICS_FINDINGS, finding))


def get_mechanics_finding(
    conn: sqlite3.Connection, finding_id: str
) -> MechanicsFinding | None:
    return cast(MechanicsFinding | None, _get(conn, _MECHANICS_FINDINGS, finding_id))


def list_mechanics_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MechanicsFinding]:
    return cast(
        list[MechanicsFinding], _list(conn, _MECHANICS_FINDINGS, limit=limit, **filters)
    )


def save_persona_reaction(conn: sqlite3.Connection, reaction: PersonaReaction) -> str:
    return cast(str, _save(conn, _PERSONA_REACTIONS, reaction))


def get_persona_reaction(
    conn: sqlite3.Connection, reaction_id: str
) -> PersonaReaction | None:
    return cast(PersonaReaction | None, _get(conn, _PERSONA_REACTIONS, reaction_id))


def list_persona_reactions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PersonaReaction]:
    return cast(
        list[PersonaReaction], _list(conn, _PERSONA_REACTIONS, limit=limit, **filters)
    )


def save_audience_scorecard(
    conn: sqlite3.Connection, scorecard: AudienceScorecard
) -> str:
    return cast(str, _save(conn, _SCORECARDS, scorecard))


def get_audience_scorecard(
    conn: sqlite3.Connection, scorecard_id: str
) -> AudienceScorecard | None:
    return cast(AudienceScorecard | None, _get(conn, _SCORECARDS, scorecard_id))


def list_audience_scorecards(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AudienceScorecard]:
    return cast(
        list[AudienceScorecard], _list(conn, _SCORECARDS, limit=limit, **filters)
    )


def save_audience_brief(conn: sqlite3.Connection, brief: AudienceBrief) -> str:
    return cast(str, _save(conn, _AUDIENCE_BRIEFS, brief))


def get_audience_brief(conn: sqlite3.Connection, brief_id: str) -> AudienceBrief | None:
    return cast(AudienceBrief | None, _get(conn, _AUDIENCE_BRIEFS, brief_id))


def list_audience_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AudienceBrief]:
    return cast(
        list[AudienceBrief], _list(conn, _AUDIENCE_BRIEFS, limit=limit, **filters)
    )


def save_calibration_record(conn: sqlite3.Connection, record: CalibrationRecord) -> str:
    return cast(str, _save(conn, _CALIBRATION, record))


def get_calibration_record(
    conn: sqlite3.Connection, record_id: str
) -> CalibrationRecord | None:
    return cast(CalibrationRecord | None, _get(conn, _CALIBRATION, record_id))


def list_calibration_records(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CalibrationRecord]:
    return cast(
        list[CalibrationRecord], _list(conn, _CALIBRATION, limit=limit, **filters)
    )


def save_playbook_entry(
    conn: sqlite3.Connection, entry: PlaybookEntry
) -> tuple[str, str, str]:
    return cast(tuple[str, str, str], _save(conn, _PLAYBOOK, entry))


def get_playbook_entry(
    conn: sqlite3.Connection, technique: str, cohort: str, metric: str
) -> PlaybookEntry | None:
    return cast(
        PlaybookEntry | None, _get(conn, _PLAYBOOK, (technique, cohort, metric))
    )


def list_playbook_entries(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PlaybookEntry]:
    return cast(list[PlaybookEntry], _list(conn, _PLAYBOOK, limit=limit, **filters))


