"""F20 run invariants checked after every act (P03 T03.059, 16 §5.1).

Core registry (frozen, I-owned): raw manifest files unchanged, offsets inside
document bounds, and citation validity. Lane checks live in
`<package>/invariants.py` and load through `invariant_plugins` (imported at
the bottom of this module). Any violation pauses the run with status
`INVARIANT_BROKEN` (the orchestrator enforces it).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sots.storage import repo as storage_repo
from sots.storage.db import Connection


@dataclass(frozen=True)
class InvariantContext:
    """What invariant checks inspect (manifest + optional database)."""

    root: Path
    manifest: dict[str, str] = field(default_factory=dict)
    conn: Connection | None = None


Invariant = Callable[[InvariantContext], list[str]]

_INVARIANTS: dict[str, Invariant] = {}


def register_invariant(name: str) -> Callable[[Invariant], Invariant]:
    """Register a check under `name` (duplicate names rejected)."""

    def _register(check: Invariant) -> Invariant:
        if name in _INVARIANTS:
            raise ValueError(f"invariant {name!r} is already registered")
        _INVARIANTS[name] = check
        return check

    return _register


def registered_invariants() -> dict[str, Invariant]:
    """Snapshot of the registry (orchestrators + tests)."""
    return dict(_INVARIANTS)


def check_all(ctx: InvariantContext) -> dict[str, list[str]]:
    """Run every invariant; name -> violations (empty list = pass)."""
    return {name: check(ctx) for name, check in sorted(_INVARIANTS.items())}


@register_invariant("raw_unchanged")
def _raw_unchanged(ctx: InvariantContext) -> list[str]:
    """Every manifest file still matches its ingest sha256."""
    violations: list[str] = []
    for rel_path, expected in sorted(ctx.manifest.items()):
        path = ctx.root / rel_path
        if not path.is_file():
            violations.append(f"{rel_path}: file missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            violations.append(f"{rel_path}: sha256 mismatch")
    return violations


@register_invariant("offsets_intact")
def _offsets_intact(ctx: InvariantContext) -> list[str]:
    """Units sit inside their document bounds (incl. revision offsets)."""
    if ctx.conn is None:
        return ["units table unavailable (no database)"]
    violations: list[str] = []
    documents = {doc.id: doc for doc in storage_repo.list_documents(ctx.conn)}
    for unit in storage_repo.list_units(ctx.conn):
        doc = documents.get(unit.document_id)
        if doc is None:
            violations.append(f"{unit.id}: document {unit.document_id} missing")
            continue
        pairs = [("offsets", unit.start_char, unit.end_char)]
        pairs.extend(
            (f"revision_offsets[{rev}]", *span)
            for rev, span in unit.revision_offsets.items()
        )
        for label, start, end in pairs:
            if not (0 <= start <= end <= doc.char_count):
                violations.append(
                    f"{unit.id}: {label} [{start}, {end}] outside 0..{doc.char_count}"
                )
    return violations


@register_invariant("cited_ids_exist")
def _cited_ids_exist(ctx: InvariantContext) -> list[str]:
    """Every evidence unit, findings unit, and findings evidence id exists."""
    if ctx.conn is None:
        return ["tables unavailable (no database)"]
    violations: list[str] = []
    unit_ids = {unit.id for unit in storage_repo.list_units(ctx.conn)}
    evidence_ids = {row.id for row in storage_repo.list_evidence(ctx.conn)}
    for row in storage_repo.list_evidence(ctx.conn):
        if row.unit_id not in unit_ids:
            violations.append(f"evidence {row.id}: unit {row.unit_id} missing")
    for findings in storage_repo.list_specialist_findings(ctx.conn):
        if findings.unit_id not in unit_ids:
            violations.append(f"findings {findings.unit_id}/{findings.specialist}: unit missing")
        for evidence_id in findings.evidence_ids:
            if evidence_id not in evidence_ids:
                violations.append(f"findings {findings.unit_id}: evidence {evidence_id} missing")
    return violations


# Bottom import: lane plugins register after the core registry exists.
# (Partial-init safe: lane modules only need `register_invariant`, defined
# above. E402 does not apply to this deliberate late binding.)
from sots.agents.failsafes import invariant_plugins  # noqa: E402,F401
