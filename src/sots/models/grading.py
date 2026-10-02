"""Quality gate grader models (17 sections 4 and 6). All frozen, extra forbidden."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CriterionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    type: Literal["hard", "measured", "judged"]
    score: float
    floor: float
    evidence: str
    judges: dict[str, float] = {}


class GradeRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    artifact_type: str
    artifact_id: str
    attempt: int
    rubric_id: str
    rubric_version: int
    criteria: list[CriterionResult]
    score: float
    passed: bool
    feedback_for_generator: list[str]
    created_at: datetime


class GraderHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_grades: int
    first_attempt_pass_rate: float
    author_reject_rate: float
    pass_within_max_rate: float
    tiebreak_rate: float
    too_lenient: bool
    too_strict: bool
    judge_disagreement: bool
    top_rejection_reasons: list[str]
