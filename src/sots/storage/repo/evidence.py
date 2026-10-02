"""evidence persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.document import SupplementDoc
from sots.models.evidence import (
    Evidence,
    FetchedDoc,
    SearchHit,
)
from sots.models.verdict import (
    DiscoveryNote,
    SpecialistFindings,
    VerdictRecord,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _DISCOVERY_NOTES,
    _EVIDENCE,
    _FETCHED_DOCS,
    _SEARCH_HITS,
    _SPECIALIST_FINDINGS,
    _SUPPLEMENT_DOCS,
    _VERDICTS,
)


def save_evidence(conn: sqlite3.Connection, evidence: Evidence) -> str:
    return cast(str, _save(conn, _EVIDENCE, evidence))


def get_evidence(conn: sqlite3.Connection, evidence_id: str) -> Evidence | None:
    return cast(Evidence | None, _get(conn, _EVIDENCE, evidence_id))


def list_evidence(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Evidence]:
    return cast(list[Evidence], _list(conn, _EVIDENCE, limit=limit, **filters))


def save_fetched_doc(conn: sqlite3.Connection, doc: FetchedDoc) -> str:
    return cast(str, _save(conn, _FETCHED_DOCS, doc))


def get_fetched_doc(conn: sqlite3.Connection, url: str) -> FetchedDoc | None:
    return cast(FetchedDoc | None, _get(conn, _FETCHED_DOCS, url))


def list_fetched_docs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[FetchedDoc]:
    return cast(list[FetchedDoc], _list(conn, _FETCHED_DOCS, limit=limit, **filters))


def save_supplement_doc(conn: sqlite3.Connection, doc: SupplementDoc) -> str:
    return cast(str, _save(conn, _SUPPLEMENT_DOCS, doc))


def get_supplement_doc(conn: sqlite3.Connection, path: str) -> SupplementDoc | None:
    return cast(SupplementDoc | None, _get(conn, _SUPPLEMENT_DOCS, path))


def list_supplement_docs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SupplementDoc]:
    return cast(
        list[SupplementDoc], _list(conn, _SUPPLEMENT_DOCS, limit=limit, **filters)
    )


def save_search_hit(conn: sqlite3.Connection, hit: SearchHit) -> int:
    return cast(int, _save(conn, _SEARCH_HITS, hit))


def get_search_hit(conn: sqlite3.Connection, hit_id: int) -> SearchHit | None:
    return cast(SearchHit | None, _get(conn, _SEARCH_HITS, hit_id))


def list_search_hits(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SearchHit]:
    return cast(list[SearchHit], _list(conn, _SEARCH_HITS, limit=limit, **filters))


def save_verdict(conn: sqlite3.Connection, record: VerdictRecord) -> str:
    return cast(str, _save(conn, _VERDICTS, record))


def get_verdict(conn: sqlite3.Connection, verdict_id: str) -> VerdictRecord | None:
    return cast(VerdictRecord | None, _get(conn, _VERDICTS, verdict_id))


def list_verdicts(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VerdictRecord]:
    return cast(list[VerdictRecord], _list(conn, _VERDICTS, limit=limit, **filters))


def save_discovery_note(conn: sqlite3.Connection, note: DiscoveryNote) -> str:
    return cast(str, _save(conn, _DISCOVERY_NOTES, note))


def get_discovery_note(conn: sqlite3.Connection, note_id: str) -> DiscoveryNote | None:
    return cast(DiscoveryNote | None, _get(conn, _DISCOVERY_NOTES, note_id))


def list_discovery_notes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DiscoveryNote]:
    return cast(list[DiscoveryNote], _list(conn, _DISCOVERY_NOTES, limit=limit, **filters))


def save_specialist_findings(
    conn: sqlite3.Connection, findings: SpecialistFindings
) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _SPECIALIST_FINDINGS, findings))


def get_specialist_findings(
    conn: sqlite3.Connection, unit_id: str, specialist: str
) -> SpecialistFindings | None:
    return cast(
        SpecialistFindings | None, _get(conn, _SPECIALIST_FINDINGS, (unit_id, specialist))
    )


def list_specialist_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SpecialistFindings]:
    return cast(
        list[SpecialistFindings], _list(conn, _SPECIALIST_FINDINGS, limit=limit, **filters)
    )


