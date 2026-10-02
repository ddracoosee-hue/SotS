"""LLM response cache entry (P02 T02.014; table `cache`)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CacheEntry(BaseModel):
    """One cached LLM result, keyed by the T02.014 input hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    value: str
    created_at: datetime
    expires_at: datetime | None = None
