"""F06 checkpointing over the `checkpoints` table (P03 T03.045, 16 §5.1).

State is saved after every agent step under a stable `checkpoint_key`. Each
envelope carries a sha256 hash; a mismatch raises CheckpointCorruptError so
the runtime restarts from scratch instead of resuming garbage.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sots.errors import CheckpointCorruptError
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


def _envelope(state: dict[str, Any]) -> dict[str, Any]:
    canonical = json.dumps(state, sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"state": state, "sha256": digest}


def save_state(conn: Connection, key: str, run_id: str, state: dict[str, Any]) -> str:
    """Save checkpointed state (upsert on key)."""
    return storage_repo.save_checkpoint(conn, key, _envelope(state), run_id=run_id)


def load_state(conn: Connection, key: str) -> dict[str, Any] | None:
    """Load checkpointed state; None when absent, corrupt → raises."""
    row = storage_repo.get_checkpoint(conn, key)
    if row is None:
        return None
    envelope = row["state"]
    if not isinstance(envelope, dict) or "state" not in envelope or "sha256" not in envelope:
        raise CheckpointCorruptError(f"checkpoint {key!r} has a malformed envelope")
    canonical = json.dumps(envelope["state"], sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if digest != envelope["sha256"]:
        raise CheckpointCorruptError(f"checkpoint {key!r} hash mismatch")
    state = envelope["state"]
    if not isinstance(state, dict):
        raise CheckpointCorruptError(f"checkpoint {key!r} state is not an object")
    return state
