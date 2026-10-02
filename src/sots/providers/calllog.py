"""LLM call logging + cost summaries (P02 T02.017, R-LLM-04).

Every attempt is written to `llm_calls` with its status
(ok/cached/invalid_retry/failed); `summarize()` aggregates rows for
`sots cost`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from sots.models.ids import new_id
from sots.models.run import LLMCall
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

CallStatus = Literal["ok", "cached", "invalid_retry", "failed"]


class CostRow(BaseModel):
    """Aggregated spend for one (task, provider) pair (`sots cost`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    provider: str
    calls: int
    input_tokens: int
    output_tokens: int
    cost: float


def write_call(
    conn: Connection,
    *,
    run_id: str | None,
    task: str,
    provider: str,
    model: str,
    prompt_id: str,
    prompt_version: int,
    input_hash: str,
    input_tokens: int,
    output_tokens: int,
    cost_estimate: float,
    latency_ms: int,
    status: CallStatus,
    fallback_used: bool = False,
) -> str:
    """Append one LLMCall row; returns the call id (R-LLM-04)."""
    call = LLMCall(
        id=new_id("call"),
        run_id=run_id,
        task=task,
        provider=provider,
        model=model,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        input_hash=input_hash,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost_estimate,
        latency_ms=latency_ms,
        status=status,
        created_at=datetime.now(UTC),
        fallback_used=fallback_used,
    )
    return storage_repo.save_llm_call(conn, call)


def summarize(conn: Connection, since: datetime | None = None) -> list[CostRow]:
    """Aggregate llm_calls by (task, provider), optionally filtered by date."""
    rows = storage_repo.list_llm_calls(conn)
    totals: dict[tuple[str, str], dict[str, float | int]] = {}
    for call in rows:
        if since is not None and call.created_at.replace(tzinfo=None) < since.replace(tzinfo=None):
            continue
        key = (call.task, call.provider)
        slot = totals.setdefault(key, {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
        slot["calls"] += 1
        slot["in"] += call.input_tokens
        slot["out"] += call.output_tokens
        slot["cost"] += call.cost_estimate
    return [
        CostRow(
            task=task,
            provider=provider,
            calls=int(slot["calls"]),
            input_tokens=int(slot["in"]),
            output_tokens=int(slot["out"]),
            cost=float(slot["cost"]),
        )
        for (task, provider), slot in sorted(totals.items())
    ]
