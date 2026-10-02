"""Psyche engine models (P01 T01.008; blueprint 03 §5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .enums import Severity


class EngineFinding(BaseModel):
    """A single finding from one psyche engine (see 08 for vocabularies)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str
    engine: str
    finding_type: str
    unit_ids: list[str]
    summary: str
    detail: str
    confidence: float
    severity: Severity
    responds_to: list[str] = []
    question_for_author: str | None


class Synthesis(BaseModel):
    """Cross-engine synthesis of findings for a run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    agreements: list[str]
    tensions: list[str]
    top_insights: list[str]
    finding_ids: list[str]
