"""narrative persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.narrative import (
    CoreMessage,
    DriftReport,
    MessageMapping,
    VoiceComparison,
    VoiceFingerprint,
)
from sots.models.shadow import ShadowReport
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _CORE_MESSAGES,
    _DRIFT_REPORTS,
    _MESSAGE_MAPPINGS,
    _SHADOW_REPORTS,
    _VOICE_COMPARISONS,
    _VOICE_FINGERPRINTS,
)


def save_core_message(conn: sqlite3.Connection, message: CoreMessage) -> str:
    return cast(str, _save(conn, _CORE_MESSAGES, message))


def get_core_message(conn: sqlite3.Connection, message_id: str) -> CoreMessage | None:
    return cast(CoreMessage | None, _get(conn, _CORE_MESSAGES, message_id))


def list_core_messages(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CoreMessage]:
    return cast(list[CoreMessage], _list(conn, _CORE_MESSAGES, limit=limit, **filters))


def save_message_mapping(conn: sqlite3.Connection, mapping: MessageMapping) -> str:
    return cast(str, _save(conn, _MESSAGE_MAPPINGS, mapping))


def get_message_mapping(conn: sqlite3.Connection, unit_id: str) -> MessageMapping | None:
    return cast(MessageMapping | None, _get(conn, _MESSAGE_MAPPINGS, unit_id))


def list_message_mappings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MessageMapping]:
    return cast(
        list[MessageMapping], _list(conn, _MESSAGE_MAPPINGS, limit=limit, **filters)
    )


def save_drift_report(conn: sqlite3.Connection, report: DriftReport) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _DRIFT_REPORTS, report))


def get_drift_report(
    conn: sqlite3.Connection, run_id: str, document_id: str
) -> DriftReport | None:
    return cast(
        DriftReport | None, _get(conn, _DRIFT_REPORTS, (run_id, document_id))
    )


def list_drift_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DriftReport]:
    return cast(list[DriftReport], _list(conn, _DRIFT_REPORTS, limit=limit, **filters))


def save_voice_fingerprint(conn: sqlite3.Connection, fingerprint: VoiceFingerprint) -> int:
    return cast(int, _save(conn, _VOICE_FINGERPRINTS, fingerprint))


def get_voice_fingerprint(
    conn: sqlite3.Connection, fingerprint_id: int
) -> VoiceFingerprint | None:
    return cast(VoiceFingerprint | None, _get(conn, _VOICE_FINGERPRINTS, fingerprint_id))


def list_voice_fingerprints(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VoiceFingerprint]:
    return cast(
        list[VoiceFingerprint], _list(conn, _VOICE_FINGERPRINTS, limit=limit, **filters)
    )


def save_voice_comparison(conn: sqlite3.Connection, comparison: VoiceComparison) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _VOICE_COMPARISONS, comparison))


def get_voice_comparison(
    conn: sqlite3.Connection, run_id: str, document_id: str
) -> VoiceComparison | None:
    return cast(
        VoiceComparison | None, _get(conn, _VOICE_COMPARISONS, (run_id, document_id))
    )


def list_voice_comparisons(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VoiceComparison]:
    return cast(
        list[VoiceComparison], _list(conn, _VOICE_COMPARISONS, limit=limit, **filters)
    )


def save_shadow_report(conn: sqlite3.Connection, report: ShadowReport) -> str:
    return cast(str, _save(conn, _SHADOW_REPORTS, report))


def get_shadow_report(conn: sqlite3.Connection, report_id: str) -> ShadowReport | None:
    return cast(ShadowReport | None, _get(conn, _SHADOW_REPORTS, report_id))


def list_shadow_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ShadowReport]:
    return cast(list[ShadowReport], _list(conn, _SHADOW_REPORTS, limit=limit, **filters))


