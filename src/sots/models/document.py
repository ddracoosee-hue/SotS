"""Document and Chunk models (03 §2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Document(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    source_path: str
    inbox_path: str
    sha256: str
    title: str
    chapter_id: str | None
    char_count: int
    word_count: int
    ingested_at: datetime


class Chunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    document_id: str
    index: int
    start_char: int
    end_char: int
    token_estimate: int


class SupplementDoc(BaseModel):
    """One indexed file from supplements/ (P04 T04.015)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    sha256: str
    text: str
    indexed_at: datetime
