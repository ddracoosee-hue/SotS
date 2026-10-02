"""F08 dead-letter queue over the `dead_letters` table (P03 T03.047, 16 §5.1).

Items that fail permanently land here with the full reason + inputs for the
TUI Review queue; `retry` pulls one back out for an individual re-run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from sots.storage import repo as storage_repo
from sots.storage.db import Connection


class DeadLetter(BaseModel):
    """One dead-lettered item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    run_id: str | None
    agent: str
    team: str
    payload: dict[str, Any]
    error: str
    created_at: datetime


def _coerce(row: dict[str, Any]) -> DeadLetter:
    created = row["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    return DeadLetter(
        id=int(row["id"]), run_id=row["run_id"], agent=row["agent"], team=row["team"],
        payload=dict(row["payload"]), error=row["error"], created_at=created,
    )


def send(
    conn: Connection, *, run_id: str | None, agent: str, team: str,
    payload: dict[str, Any], error: str,
) -> int:
    """Dead-letter an item; returns its row id."""
    return storage_repo.save_dead_letter(
        conn, agent, team, payload, error, run_id=run_id
    )


def list_items(conn: Connection, *, run_id: str | None = None) -> list[DeadLetter]:
    """Dead letters, oldest first (optionally for one run)."""
    return [_coerce(row) for row in storage_repo.list_dead_letters(conn, run_id=run_id)]


def retry(conn: Connection, item_id: int) -> DeadLetter:
    """Pull one item for re-run (deleted from the queue)."""
    row = storage_repo.get_dead_letter(conn, item_id)
    if row is None:
        raise ValueError(f"dead letter {item_id} not found")
    storage_repo.delete_dead_letter(conn, item_id)
    return _coerce(row)
