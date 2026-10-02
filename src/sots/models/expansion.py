"""Expansion Team models (11 section 3). All frozen, extra forbidden."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Origin(StrEnum):
    AUTHOR = "author"
    SOURCE = "source"
    SYSTEM = "system"


class Concept(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    label: str
    definition: str
    unit_ids: list[str]
    chapter_ids: list[str]
    message_ids: list[str]
    maturity: Literal["seed", "developing", "developed"]


class ConceptEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str
    target_id: str
    relation: Literal[
        "causes",
        "enables",
        "contrasts",
        "exemplifies",
        "extends",
        "parallels",
        "resolves",
        "tension_with",
    ]
    rationale: str
    unit_ids: list[str]
    inferred: bool


class ConceptGraph(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    concepts: list[Concept]
    edges: list[ConceptEdge]
    hubs: list[str]
    bridges: list[str]
    orphans: list[str]


class ExpansionThread(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    kind: Literal["deepen", "connect", "challenge", "contextualize", "evidence_gap"]
    concept_ids: list[str]
    message_ids: list[str]
    rationale: str
    estimated_tokens: int
    status: Literal[
        "proposed", "approved", "researching", "reported", "integrated", "rejected", "failed"
    ]
    critic_score: float | None


class ResearchBrief(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    thread_id: str
    central_question: str
    why_it_matters: str
    author_starting_point: list[str]
    sub_questions: list[str]
    must_find: list[
        Literal[
            "statistic",
            "study",
            "meta_analysis",
            "legal_case",
            "historical_context",
            "expert_view",
            "counter_view",
            "lived_experience_accounts",
            "media_example",
        ]
    ]
    exclusions: list[str]
    max_depth: int
    max_sources: int


class ResearchNote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    thread_id: str
    sub_question: str
    claim: str
    evidence_id: str
    depth: int
    novelty: float
    leads: list[str]


class ReportStatement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    origin: Origin
    note_ids: list[str]
    unit_ids: list[str]


class ReportSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading: str
    statements: list[ReportStatement]


class DeepResearchReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    thread_id: str
    title: str
    executive_summary: list[ReportStatement]
    sections: list[ReportSection]
    counter_perspectives: ReportSection
    connections_to_author_text: ReportSection
    new_concepts: list[Concept]
    open_questions: list[str]
    source_mix: dict[str, int]
    saturation_curve: list[float]


class MarginNote(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    unit_id: str
    kind: Literal[
        "connects_to",
        "deeper_question",
        "counterpoint",
        "supporting_research",
        "reader_question",
        "concept_link",
        "echo",
    ]
    text: str
    origin: Origin
    links: list[str]
    status: Literal["open", "kept", "dismissed"]


class IntegrationBrief(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    report_id: str
    chapter_id: str
    placements: list[dict]
    new_message_candidates: list[str]
    restructure_suggestions: list[str]
    questions_for_author: list[str]
    risks: list[str]


class CriticScore(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_id: str
    relevance: float
    grounding: float
    novelty: float
    voice_respect: float
    balance: float
    verdict: Literal["accept", "revise", "reject"]
    reasons: list[str]
