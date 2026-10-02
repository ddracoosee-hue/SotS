"""Embedded claims become child units (P06 T06.005, 05 §3.3).

Each embedded item becomes a Unit with the parent's span (a pointer into the
parent's text), inherited entities, and `parent_unit_id` set. Children arrive
unclassified; the stage re-classifies them as FACTUAL_CLAIM (depth 1 only).
"""

from __future__ import annotations

from collections.abc import Sequence

from sots.models.ids import new_id
from sots.models.unit import Unit


def spawn_children(
    parent: Unit, embedded_claims: Sequence[str], *, run_id: str
) -> list[Unit]:
    """Unclassified child units for a parent's embedded claims (05 §3.3)."""
    children: list[Unit] = []
    for claim in embedded_claims:
        text = claim.strip()
        if not text:
            continue
        children.append(Unit(
            id=new_id("unit"), document_id=parent.document_id,
            chunk_id=parent.chunk_id, run_id=run_id, order=parent.order,
            text=text, start_char=parent.start_char, end_char=parent.end_char,
            entities=list(parent.entities), parent_unit_id=parent.id,
        ))
    return children
