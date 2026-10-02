"""Agent runtime models (16). All frozen, extra forbidden."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

KNOWN_FAILSAFE_IDS = frozenset(
    f"F{i:02d}" for i in range(1, 21)
)


class AgentCardPrompts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    system: str
    step: str


class AgentLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_steps: int
    max_tokens: int
    timeout_s: int
    max_retries: int


class AgentGrading(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rubric: str | None = None


class AgentCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    team: str
    role: str
    prompts: AgentCardPrompts
    output_model: str
    routing_task: str
    tools: list[str]
    internet: bool
    limits: AgentLimits
    grading: AgentGrading = AgentGrading()
    failsafes: list[str]
    foundation_pieces: list[str] = []
    on_failure: Literal["dead_letter", "escalate_to_author", "degrade"]

    @field_validator("failsafes")
    @classmethod
    def _reject_unknown_failsafes(cls, value: list[str]) -> list[str]:
        unknown = [f for f in value if f not in KNOWN_FAILSAFE_IDS]
        if unknown:
            raise ValueError(f"unknown failsafe ids: {unknown}")
        return value


class AgentAction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["tool", "final"]
    tool: str | None
    args: dict | None
    thought: str
    final: dict | None


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: str
    ok: bool
    content: str
    truncated: bool


class AgentRun(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str
    agent: str
    team: str
    act: str
    started_at: datetime
    finished_at: datetime | None
    steps: int
    tokens_in: int
    tokens_out: int
    cost: float
    status: Literal["ok", "failed", "dead_letter", "escalated", "degraded", "cancelled"]
    failure_code: str | None
    grade_attempts: int
    final_grade: float | None
    checkpoint_key: str


class AgentResult[T](BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent: str
    status: Literal["ok", "failed", "dead_letter", "escalated", "degraded", "cancelled"]
    output: T | None = None
    error: str | None = None


class BudgetSlice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scope: str
    tokens_allowed: int
    tokens_used: int = 0
    cost_allowed: float
    cost_used: float = 0.0
