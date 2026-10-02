"""Legal Chamber models (P01 T01.019; blueprint 22 §5)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .enums import Severity


class LegalIssue(BaseModel):
    """One flagged legal exposure, assigned to counsel (22 §2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str
    revision_id: str
    unit_ids: list[str]
    issue_types: list[
        Literal[
            "defamation",
            "false_light",
            "privacy",
            "consent",
            "copyright",
            "trademark",
            "court_record",
            "health_claim",
            "consumer_protection",
            "jurisdiction",
            "ethics",
            "contract_nda",
            "other",
        ]
    ]
    persons_involved: list[dict]
    preliminary_risk: Severity
    assigned_counsel: list[str]
    status: Literal["open", "in_deliberation", "resolved", "edited", "blocked", "waived"]


class Authority(BaseModel):
    """A fetched, excerpt-verified legal authority (22 §4.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[
        "statute",
        "case",
        "regulation",
        "agency_guidance",
        "treatise_or_article",
        "publisher_standard",
    ]
    citation: str
    jurisdiction: str
    evidence_id: str


class Position(BaseModel):
    """One counsel's argued position on an issue (22 §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    issue_id: str
    counsel: str
    round: int
    stance: Literal[
        "safe_as_is", "safe_with_edits", "risky_needs_major_change", "cut", "needs_attorney"
    ]
    risk: Severity
    argument: str
    authorities: list[Authority]
    proposed_edits: list[dict]
    rebuttals: list[dict]
    argument_score: float | None


class DefenseMemo(BaseModel):
    """The cohesive, evidence-backed defense argument (22 §4)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    issue_id: str
    text_position: str
    defense_basis: list[
        Literal[
            "truth_substantial_truth",
            "opinion",
            "fair_report",
            "public_interest",
            "consent",
            "fair_use",
            "de_minimis",
            "anonymization",
            "disclaimer",
            "not_of_and_concerning",
        ]
    ]
    argument: str
    required_edits: list[dict]
    residual_risk: Severity
    answered_dissents: list[dict]
    endorsements: dict[str, Literal["endorse", "endorse_with_reservations", "dissent"]]
    grade_id: str
    needs_licensed_attorney: bool
