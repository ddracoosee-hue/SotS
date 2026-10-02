"""Narrative and voice models (P01 T01.009; blueprint 03 §6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class CoreMessage(BaseModel):
    """A core message from profile/messages.yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    level: Literal["book", "chapter"]
    chapter_id: str | None
    statement: str
    priority: int


class MessageMapping(BaseModel):
    """How one unit serves (or ignores) a core message."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    message_id: str | None
    role: Literal[
        "states", "illustrates", "supports_with_evidence", "counters", "transitions", "none"
    ]
    strength: float


class DriftReport(BaseModel):
    """Message coverage and drift analysis for a document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    document_id: str
    coverage: dict[str, float]
    unmapped_ratio: float
    drift_segments: list[tuple[int, int]]
    missing_messages: list[str]
    flow_breaks: list[str]


class VoiceFingerprint(BaseModel):
    """Quantitative + LLM voice profile of a corpus or document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Literal["voice_corpus", "document"]
    avg_sentence_len: float
    sentence_len_stdev: float
    type_token_ratio: float
    punctuation_profile: dict[str, float]
    person_ratio: dict[str, float]
    signature_phrases: list[str]
    llm_style_description: str


class VoiceComparison(BaseModel):
    """Similarity of a document's voice to the author's voice corpus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    document_id: str
    similarity: float
    deviations: list[str]
    off_voice_unit_ids: list[str]
