"""F07 idempotency keys for persisted records (P03 T03.046, 16 §5.1).

Every persisted record keys on `(run_id, agent, input_hash)`; `persist`
writes through `repo.idempotent_save`, so a duplicate write is a no-op that
returns False instead of duplicating the row.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

from sots.storage import repo as storage_repo
from sots.storage.db import Connection


def input_hash(payload: dict[str, Any]) -> str:
    """Stable sha256 over canonical JSON (dict key for one input)."""
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def idempotency_key(run_id: str, agent: str, digest: str) -> str:
    """Deterministic key for (run_id, agent, input_hash)."""
    return hashlib.sha256(f"{run_id}\n{agent}\n{digest}".encode()).hexdigest()


def persist(conn: Connection, model: BaseModel, *, run_id: str, agent: str, digest: str) -> bool:
    """Idempotent write; True when the row was written, False on duplicate."""
    return storage_repo.idempotent_save(conn, model, idempotency_key(run_id, agent, digest))
