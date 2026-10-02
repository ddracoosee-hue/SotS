"""Learning loop models (P01 T01.020; blueprint 20 §7)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LearningChange(BaseModel):
    """A versioned, author-approved learned change (20 §7, LR-01 to LR-03)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: Literal["prompt", "threshold", "rubric", "persona"]
    target: str
    before: str
    after: str
    evidence: str
    status: Literal["proposed", "applied", "dismissed"]
    applied_at: datetime | None


class PromptTrial(BaseModel):
    """A/B of a candidate prompt version on replays + gold sets (20 §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    prompt_id: str
    baseline_version: int
    candidate_version: int
    metric_deltas: dict[str, float]
    release_blocker_regressions: list[str]
    promoted: bool
