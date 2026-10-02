"""Author/book/chapter profile models (P01 T01.011; blueprint 03 §8).

.. note:: Provisional — field shapes will be finalized after the author
   provides the chapter briefs (see 15_OPEN_ITEMS.md).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthorProfile(BaseModel):
    """Who the author is. Provisional shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name_or_pen_name: str
    background: str
    why_this_book: str
    lived_experience_areas: list[str]
    sensitive_topics: list[str]
    values: list[str]
    known_biases_self_reported: list[str]


class BookProfile(BaseModel):
    """What the book is. Provisional shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    working_title: str
    genre: Literal["self_help_reflective"]
    premise: str
    target_reader: str
    promise_to_reader: str
    tone_goals: list[str]
    out_of_scope: list[str]
    media_exclusions: list[str]


class ChapterBrief(BaseModel):
    """The author's brief for one chapter. Provisional shape."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str
    title: str
    purpose: str
    key_messages: list[str]
    planned_stories: list[str]
    planned_references: list[str]
    reader_takeaway: str
    raw_brief: str
    reader_journey: str | None = None


class VoiceSample(BaseModel):
    """One voice-corpus manifest entry (P04 T04.001; registers owned by P11A)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str
    path: str
    voice_register: str = Field(alias="register")
    written_on: str | None = None
    words: int | None = None
    weight: float = 1.0
    sha256: str | None = None
    note: str | None = None


class VoiceManifest(BaseModel):
    """The voice_corpus manifest (version defaults for fresh checkouts)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = 1
    samples: list[VoiceSample] = []
