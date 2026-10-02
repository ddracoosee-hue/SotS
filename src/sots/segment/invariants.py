"""Segment lane invariants (moved from f20 in W0; imported by invariant_plugins)."""

from __future__ import annotations

from pathlib import Path

from sots.agents.failsafes.f20_invariants import (
    InvariantContext,
    register_invariant,
)
from sots.storage import repo as storage_repo


@register_invariant("offset_integrity")
def offset_integrity(ctx: InvariantContext) -> list[str]:
    """Top-level units equal their canonical slice; children sit in-range (05 §3.3)."""
    if ctx.conn is None:
        return ["units table unavailable (no database)"]
    violations: list[str] = []
    texts: dict[str, str | None] = {}
    documents = {doc.id: doc for doc in storage_repo.list_documents(ctx.conn)}
    units = {unit.id: unit for unit in storage_repo.list_units(ctx.conn)}
    for unit in units.values():
        if unit.parent_unit_id is not None:
            parent = units.get(unit.parent_unit_id)
            if parent is None:
                violations.append(f"{unit.id}: parent {unit.parent_unit_id} missing")
            elif not (
                parent.start_char <= unit.start_char <= unit.end_char <= parent.end_char
            ):
                violations.append(f"{unit.id}: span outside parent {parent.id}")
            continue  # child offsets point into the parent's text (05 §3.3)
        doc = documents.get(unit.document_id)
        if doc is None:
            violations.append(f"{unit.id}: document {unit.document_id} missing")
            continue
        if unit.document_id not in texts:
            canonical = Path(doc.inbox_path).parent / f"{doc.id}.txt"
            texts[unit.document_id] = (
                canonical.read_text(encoding="utf-8") if canonical.is_file() else None
            )
        text = texts[unit.document_id]
        if text is None:
            violations.append(f"{unit.id}: canonical text for {doc.id} missing")
            continue
        if not 0 <= unit.start_char <= unit.end_char <= len(text):
            violations.append(f"{unit.id}: offsets outside canonical text")
        elif text[unit.start_char:unit.end_char] != unit.text:
            violations.append(
                f"{unit.id}: text mismatch at [{unit.start_char}, {unit.end_char}]"
            )
    return violations
