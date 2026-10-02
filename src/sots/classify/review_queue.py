"""Review queue: query + author relabel (P06 T06.006, 05 §3.4).

Units below `settings.classify.review_threshold` (or unclassified) queue for
the author unless already author-labeled. A human label always overrides the
model and is stored with `labeled_by = "author"`.
"""

from __future__ import annotations

from typing import Any

from sots.models.unit import Unit
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

#: Unit fields the author may relabel (classification only).
RELABEL_FIELDS = frozenset({
    "content_type", "claim_kind", "media_kind", "checkability", "entities",
    "normalized_claim", "classify_confidence",
})


def needs_review(
    conn: Connection, *, run_id: str | None = None, threshold: float
) -> list[Unit]:
    """Model-labeled units under the confidence threshold (05 §3.4)."""
    if run_id is None:
        units = storage_repo.list_units(conn)
    else:
        units = storage_repo.list_units(conn, run_id=run_id)
    return [
        unit for unit in units
        if unit.labeled_by == "model" and (
            unit.classify_confidence is None or unit.classify_confidence < threshold
        )
    ]


def relabel(conn: Connection, unit_id: str, fields: dict[str, Any]) -> Unit:
    """Apply an author label (revalidated + stored as author-labeled)."""
    unknown = set(fields) - RELABEL_FIELDS
    if unknown:
        raise ValueError(f"cannot relabel fields: {sorted(unknown)}")
    unit = storage_repo.get_unit(conn, unit_id)
    if unit is None:
        raise KeyError(f"unknown unit {unit_id!r}")
    updated = Unit.model_validate({
        **unit.model_dump(), **fields, "labeled_by": "author",
    })
    storage_repo.save_unit(conn, updated)
    return updated
