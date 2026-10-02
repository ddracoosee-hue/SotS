"""Ingest lane invariants (moved from f20 in W0; imported by invariant_plugins)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sots.agents.failsafes.f20_invariants import (
    InvariantContext,
    register_invariant,
)
from sots.storage import repo as storage_repo


@register_invariant("raw_files_unchanged")
def raw_files_unchanged(ctx: InvariantContext) -> list[str]:
    """Every ingested inbox original still matches its Document sha256 (P04 T04.016)."""
    if ctx.conn is None:
        return ["documents table unavailable (no database)"]
    violations: list[str] = []
    for doc in storage_repo.list_documents(ctx.conn):
        path = Path(doc.inbox_path)
        if not path.is_file():
            violations.append(f"{doc.id}: inbox file missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != doc.sha256:
            violations.append(f"{doc.id}: inbox file sha256 mismatch")
    return violations
