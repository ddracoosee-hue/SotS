"""Unit model (03 §2); mutable, with revision_offsets (19 §1.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sots.models.enums import Checkability, ClaimKind, ContentType, MediaKind

#: Author-declared provenance classes (25 §7.2, R-PROV-01).
AuthorProvenance = Literal["live_source", "belief", "experience", "opinion"]


class Unit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    document_id: str
    chunk_id: str
    run_id: str
    order: int
    text: str
    start_char: int
    end_char: int
    content_type: ContentType | None = None
    claim_kind: ClaimKind | None = None
    media_kind: MediaKind | None = None
    checkability: Checkability | None = None
    entities: list[str] = Field(default_factory=list)
    normalized_claim: str | None = None
    classify_confidence: float | None = None
    safety_flag: bool = False
    parent_unit_id: str | None = None
    block: int | None = None
    prompt_id: str | None = None
    anchor_ids: list[str] = Field(default_factory=list)
    author_provenance: AuthorProvenance | None = None
    source_ref: str | None = None
    serial: str | None = None
    labeled_by: Literal["model", "author"] = "model"
    revision_offsets: dict[str, tuple[int, int]] = Field(default_factory=dict)
