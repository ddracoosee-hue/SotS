"""Shadow Self models (P01 T01.010; blueprint 03 §7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .enums import Severity


class ShadowItem(BaseModel):
    """One shadow observation about the author's text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: Literal[
        "contradiction",
        "avoidance",
        "self_serving_frame",
        "unearned_lesson",
        "harshness_asymmetry",
        "fact_risk",
        "overreach",
    ]
    unit_ids: list[str]
    observation: str
    question_for_author: str
    severity: Severity


class RubricScore(BaseModel):
    """Score for one rubric criterion from config/rubrics.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    criterion_id: str
    score: int
    measured_value: float | None
    target: float | None
    met: bool
    justification: str
    unit_ids: list[str]


class ShadowReport(BaseModel):
    """Full shadow report for a document in a run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str
    document_id: str
    items: list[ShadowItem]
    scores: list[RubricScore]
    overall: float
    goals_met: int
    goals_total: int
    trend_vs_previous: dict[str, float]
