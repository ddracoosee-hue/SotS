"""Verdict models (03 §3) plus SpecialistFindings and DiscoveryNote (06 §9)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sots.models.enums import SourceClass, Verdict


class RuleCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule_id: str
    passed: bool
    cap: Verdict | None
    note: str


class VerdictRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    unit_id: str
    run_id: str
    proposed_verdict: Verdict
    final_verdict: Verdict
    truth_basis: SourceClass | None
    confidence: float
    evidence_ids: list[str]
    researcher_summary: str
    skeptic_objections: list[str]
    adjudicator_reasoning: str
    rule_checks: list[RuleCheck]
    what_is_accurate: str
    what_is_off: str
    suggested_correction: str | None
    claim_specific: dict
    epistemic_tier: str | None = None
    tier_claimed_by_author: str | None = None


class SpecialistFindings(BaseModel):
    """Handoff from a fact-check specialist to the Researcher (06 §9.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    specialist: str
    evidence_ids: list[str] = Field(default_factory=list)
    claim_specific: dict = Field(default_factory=dict)


class DiscoveryNote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    unit_id: str
    agent: str
    kind: Literal[
        "stronger_source",
        "better_example",
        "newer_data",
        "counterpoint",
        "related_case",
        "related_study",
        "media_mention",
    ]
    summary: str
    evidence_id: str
    why_interesting: str
