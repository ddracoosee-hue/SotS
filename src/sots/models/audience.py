"""Audience Lab models (P01 T01.018; blueprint 20)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from sots.errors import AdultsOnlyViolation

from .enums import Severity


class Persona(BaseModel):
    """One adult persona card from `config/personas.yaml` (20 §4.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    cohort: Literal["gen_z_adult", "millennial", "gen_x"]
    age: int
    life_stage: str
    region: str
    background_notes: str
    reading_habits: str
    need_for_cognition: Literal["high", "medium"]
    current_season: str
    skepticism: str
    values: list[str]
    what_would_make_them_close_the_book: str

    @field_validator("age")
    @classmethod
    def _adults_only(cls, value: int) -> int:
        if value < 18:
            raise AdultsOnlyViolation(f"persona age {value}: the panel is adults only")
        return value


class QuoteRef(BaseModel):
    """A quote (≤ 25 words) pinned to a unit, with a note (20 §4.3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    quote: str
    note: str = ""


class MechanicsFinding(BaseModel):
    """One finding from the Text Mechanics Panel (20 §3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    analyst: Literal["phrasing", "pacing", "tonality", "context"]
    revision_id: str
    unit_ids: list[str]
    metric: str | None
    value: float | None
    threshold: float | None
    issue: str
    suggestion: str
    severity: Severity


class PersonaReaction(BaseModel):
    """One persona's read of one section (20 §4.3). Scores are 0-10."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    persona_id: str
    sample: int
    revision_id: str
    section_id: str
    first_impression: str
    felt: list[str]
    recognition: float
    felt_judged: float
    curiosity: float
    absorption: float
    insight: float
    agency: float
    preachiness: float
    credibility: float
    intellectual_respect: float
    relatability: float
    would_continue: float
    would_share: float
    confusing_parts: list[QuoteRef]
    cringe_parts: list[QuoteRef]
    strongest_line: QuoteRef | None
    takeaway_in_own_words: str
    disagreements: list[QuoteRef]
    question_for_author: str | None


class AudienceScorecard(BaseModel):
    """Deterministic aggregation of a panel run (20 §5.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    revision_id: str
    metric_means: dict[str, float]
    cohort_means: dict[str, dict[str, float]]
    metric_sd: dict[str, float]
    metric_min: dict[str, float]
    metric_max: dict[str, float]
    message_reception_rate: float
    journey_curve: dict[str, list[float]]
    hotspots: list[str]
    strong_lines: list[str]


class BriefItem(BaseModel):
    """One prioritized fix for the rewriter (20 §5.4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_ids: list[str]
    problem: str
    evidence: str
    direction: str
    protect: list[str]


class AudienceBrief(BaseModel):
    """Ordered feedback brief for the Line Editor (20 §5.4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    revision_id: str
    scorecard_id: str
    priorities: list[BriefItem]
    do_not_touch: list[str]
    voice_cautions: list[str]


class CalibrationRecord(BaseModel):
    """Synthetic-vs-real bias and correlation per metric x cohort (20 §6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    metric: str
    cohort: str
    synthetic_mean: float
    real_mean: float
    bias: float
    correlation: float | None
    real_respondents: int
    unreliable: bool


class PlaybookEntry(BaseModel):
    """Beta(alpha, beta) posterior per technique x cohort x metric (20 §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    technique: str
    cohort: str
    metric: str
    alpha: float = 1.0
    beta: float = 1.0
    trials: int = 0
