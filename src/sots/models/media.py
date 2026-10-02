"""Media reference models (P01 T01.007; blueprint 03 §4)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .enums import MediaKind


class MediaWork(BaseModel):
    """An identified media work the author references."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: MediaKind
    title: str
    creators: list[str]
    year: int | None
    external_ids: dict[str, str]
    resolved: bool


class MediaPoint(BaseModel):
    """One checkable thing the author says about a work."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str
    point_type: Literal["plot_fact", "quote", "attribution", "character", "detail"]
    accuracy: Literal["accurate", "partly_accurate", "inaccurate", "unverifiable"]
    correction: str | None
    evidence_ids: list[str]


class MediaCheck(BaseModel):
    """Verdict on the author's use of a media work."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    unit_id: str
    run_id: str
    work: MediaWork
    points: list[MediaPoint]
    author_reading: str
    established_readings: list[str]
    interpretation_status: Literal[
        "supported_reading",
        "plausible_personal_reading",
        "contested_reading",
        "contradicted_by_source",
    ]
    message_alignment: float
    use_in_book_note: str
