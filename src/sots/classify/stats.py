"""Per-document classification counts (P06 T06.009).

Unclassified slots count under `"none"` so report rows always reconcile to
the document's unit total.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from sots.models.unit import Unit
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


class DocStats(BaseModel):
    """Classification counts for one document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    total: int
    by_content_type: dict[str, int]
    by_claim_kind: dict[str, int]
    by_checkability: dict[str, int]


def _bucket(value: StrEnum | None) -> str:
    return value.value if value is not None else "none"


def document_stats(conn: Connection, document_id: str) -> DocStats:
    """Count one document's units by type/kind/checkability."""
    units: list[Unit] = storage_repo.list_units(conn, document_id=document_id)
    by_content_type: dict[str, int] = {}
    by_claim_kind: dict[str, int] = {}
    by_checkability: dict[str, int] = {}
    for unit in units:
        for counter, value in (
            (by_content_type, unit.content_type),
            (by_claim_kind, unit.claim_kind),
            (by_checkability, unit.checkability),
        ):
            key = _bucket(value)
            counter[key] = counter.get(key, 0) + 1
    return DocStats(
        document_id=document_id, total=len(units),
        by_content_type=by_content_type, by_claim_kind=by_claim_kind,
        by_checkability=by_checkability,
    )
