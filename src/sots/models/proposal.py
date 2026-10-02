"""Proposal Desk models (18). All frozen, extra forbidden."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from sots.models.expansion import ReportStatement
from sots.models.media import MediaWork


class PlacementOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    location: Literal[
        "after_unit",
        "before_unit",
        "replace_unit",
        "new_section",
        "sidebar_box",
        "endnote",
        "epigraph",
        "chapter_opening",
        "chapter_closing",
    ]
    anchor_unit_id: str | None
    chapter_id: str
    rationale: str
    preview_outline: list[str]


class IntegrationMode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    mode: Literal[
        "brief_mention",
        "paraphrase_with_citation",
        "short_quote_with_citation",
        "extended_example",
        "author_reflection_on_it",
        "framing_device",
        "data_callout",
        "endnote_only",
    ]
    description: str
    word_estimate: int


class AuthorQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    question: str
    purpose: Literal["experience", "opinion", "memory", "permission", "preference", "fact"]
    required: bool


class Proposal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    run_id: str
    kind: str
    source_agent: str
    title: str
    pitch: str
    what_was_found: list[ReportStatement]
    connects_to_units: list[str]
    message_ids: list[str]
    media_work: MediaWork | None
    placements: list[PlacementOption]
    modes: list[IntegrationMode]
    questions: list[AuthorQuestion]
    risks: list[str]
    grade_id: str
    status: Literal[
        "queued",
        "presented",
        "discussing",
        "accepted",
        "modified",
        "deferred",
        "rejected",
        "integrated",
        "withdrawn",
    ]
    priority: float

    @field_validator("placements")
    @classmethod
    def _at_least_two_placements(cls, value: list[PlacementOption]) -> list[PlacementOption]:
        if len(value) < 2:
            raise ValueError("proposal needs at least 2 placement options")
        return value

    @field_validator("modes")
    @classmethod
    def _at_least_two_modes(cls, value: list[IntegrationMode]) -> list[IntegrationMode]:
        if len(value) < 2:
            raise ValueError("proposal needs at least 2 integration modes")
        return value

    @field_validator("questions")
    @classmethod
    def _two_to_five_questions(cls, value: list[AuthorQuestion]) -> list[AuthorQuestion]:
        if not 2 <= len(value) <= 5:
            raise ValueError("proposal needs 2-5 author questions")
        return value


class ProposalDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal_id: str
    decision: Literal["accept", "modify", "defer", "reject"]
    placement_id: str | None
    mode_id: str | None
    answers: dict[str, str]
    author_notes: str
    reject_reason: (
        Literal[
            "not_my_voice",
            "off_message",
            "dont_trust_source",
            "too_much",
            "already_covered",
            "personal_reasons",
            "legal_worry",
            "other",
        ]
        | None
    )
    decided_at: datetime


class IntegrationPlanItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    proposal_id: str
    chapter_id: str
    placement: PlacementOption
    mode: IntegrationMode
    author_answers: dict[str, str]
    evidence_ids: list[str]
    status: Literal["planned", "woven", "verified", "failed"]
