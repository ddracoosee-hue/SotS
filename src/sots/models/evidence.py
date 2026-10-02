"""Evidence, FetchedDoc (06 §3.2), and SearchHit (04 §7) models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from sots.models.enums import SourceClass, Stance


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    unit_id: str
    url: str
    title: str
    publisher: str | None
    published_date: date | None
    accessed_at: datetime
    source_class: SourceClass
    tier: int
    excerpt: str
    excerpt_match_score: float
    stance: Stance
    fetcher: str
    content_hash: str


class FetchedDoc(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    title: str
    publisher: str | None
    published_date: date | None
    text: str
    content_hash: str
    fetcher: str


class SearchHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    title: str
    snippet: str
    rank: int
