"""Polish and rewrite team models (19). All frozen, extra forbidden."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from sots.models.expansion import Origin
from sots.models.narrative import VoiceFingerprint


class RevisionHunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    revision_id: str
    unit_ids: list[str]
    before: str
    after: str
    before_span: tuple[int, int]
    change_type: Literal[
        "spelling",
        "grammar",
        "punctuation",
        "formatting",
        "clarity",
        "flow",
        "fact_correction",
        "legal_edit",
        "audience_edit",
        "woven_insert",
        "structure",
    ]
    reason: str
    agent: str
    evidence_ids: list[str] = []
    legal_issue_ids: list[str] = []
    audience_brief_id: str | None = None
    origin: Origin
    status: Literal["proposed", "auto_applied", "accepted", "rejected", "reverted"]


class Revision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    document_id: str
    chapter_id: str | None
    pass_name: Literal["A", "A_audience", "A_legal", "B"]
    parent_revision_id: str | None
    text_path: str
    sha256: str
    hunks: list[str]
    style_report_id: str | None
    cross_check_report_id: str | None
    gate_status: Literal["pending", "passed", "failed", "escalated"]


class StyleGuide(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int
    source_hash: str
    voice_summary: str
    dos: list[str]
    donts: list[str]
    protected_terms: list[str]
    intentional_patterns: list[str]
    punctuation_habits: dict[str, str]
    person_and_address: str
    rhythm_targets: dict[str, float]
    examples: list[str]


class StyleReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    revision_id: str
    fingerprint_before: VoiceFingerprint
    fingerprint_after: VoiceFingerprint
    voice_similarity: float
    per_hunk_similarity: dict[str, float]
    protected_terms_intact: float
    drift_notes: list[str]
    tone_shift: dict[str, float]
    verdict: Literal["pass", "fail"]
    fix_requests: list[str]


class CrossCheckItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str
    status: Literal[
        "match",
        "correctly_corrected",
        "drifted",
        "new_unverified_claim",
        "lost_attribution",
        "stale_source",
    ]
    note: str = ""


class CrossCheckReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    revision_id: str
    items: list[CrossCheckItem]
    pass_rate: float
    verdict: Literal["pass", "fail"]
    notes: list[str] = []
