"""Terminal persistence for agent runs (W0 split of agents/base.py)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from sots.agents.agent_state import run_usage
from sots.agents.context import AgentContext
from sots.agents.events import EventBus, emit_optional
from sots.agents.failsafes.f07_idempotency import idempotency_key, input_hash
from sots.agents.failsafes.f08_dead_letter import send as send_dead_letter
from sots.models.agents import AgentResult, AgentRun
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


async def finish_run[OutT: BaseModel](
    ctx: AgentContext,
    started: datetime,
    conn: Connection,
    bus: EventBus | None,
    *,
    status: Literal["ok", "failed", "degraded", "cancelled"],
    failure_code: str | None,
    steps: int,
    output: OutT | None = None,
    error: str | None = None,
    grade_attempts: int = 0,
    final_grade: float | None = None,
) -> AgentResult[OutT]:
    """PERSIST: AgentRun row, failure disposition, terminal event (T03.013)."""
    card = ctx.card
    final: Literal["ok", "failed", "dead_letter", "escalated", "degraded",
                   "cancelled"] = status
    if status == "failed":
        message = error or failure_code or "failed"
        if card.on_failure == "dead_letter":
            send_dead_letter(
                conn, run_id=ctx.run_id, agent=card.name,
                team=card.team,
                payload={
                    "inputs": ctx.inputs.model_dump(mode="json"),
                    "failure_code": failure_code,
                },
                error=message,
            )
            final = "dead_letter"
        elif card.on_failure == "escalate_to_author":
            final = "escalated"
        else:
            final = "degraded"
    tokens_in, tokens_out, cost = run_usage(conn, ctx.run_id)
    storage_repo.save_agent_run(
        conn,
        AgentRun(
            id=idempotency_key(
                ctx.run_id, card.name,
                input_hash(ctx.inputs.model_dump(mode="json")),
            ),
            run_id=ctx.run_id,
            agent=card.name,
            team=card.team,
            act=ctx.act,
            started_at=started,
            finished_at=datetime.now(UTC),
            steps=steps,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            status=final,
            failure_code=failure_code,
            grade_attempts=grade_attempts,
            final_grade=final_grade,
            checkpoint_key=ctx.checkpoint_key,
        ),
    )
    if final != "cancelled":
        storage_repo.delete_checkpoint(conn, ctx.checkpoint_key)
    await emit_optional(
        bus, "agent.done" if final == "ok" else "agent.failed",
        run_id=ctx.run_id, agent=card.name,
        payload={"status": final, "failure_code": failure_code, "steps": steps},
    )
    return AgentResult(
        agent=card.name, status=final, output=output, error=error
    )
