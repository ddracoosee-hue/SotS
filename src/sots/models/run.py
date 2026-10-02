"""Run and LLM call models (P01 T01.012; blueprint 03 §9)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .enums import StageStatus


class Run(BaseModel):
    """A pipeline run. Mutable: stage status and usage fill in as it executes."""

    model_config = ConfigDict(extra="forbid")

    id: str
    document_ids: list[str]
    started_at: datetime
    finished_at: datetime | None
    stage_status: dict[str, StageStatus]
    budget_tokens: int
    used_tokens: int
    cost_estimate: float
    config_snapshot: dict


class LLMCall(BaseModel):
    """One metered LLM invocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str | None
    task: str
    provider: str
    model: str
    prompt_id: str
    prompt_version: int
    input_hash: str
    input_tokens: int
    output_tokens: int
    cost_estimate: float
    latency_ms: int
    status: Literal["ok", "cached", "invalid_retry", "failed"]
    created_at: datetime
    fallback_used: bool = False  # set when routing fell back (04 §3)


class ChapterState(BaseModel):
    """Gate state for one chapter within a run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str
    act: int
    gate_status: dict[str, str]
    blocked_reasons: list[str]
