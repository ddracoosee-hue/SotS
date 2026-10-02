"""Classification output + consistency rules (P06 T06.004, 05 §3.2).

`validate_consistency` enforces the 4 code-side rules; failures come back as
the error list the classifier feeds into its retry prompt.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sots.models.enums import (
    Checkability,
    ClaimKind,
    ContentType,
    MediaKind,
)


class ClassificationOut(BaseModel):
    """One unit's classification (05 §3.2 output model)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content_type: ContentType
    claim_kind: ClaimKind | None = None
    media_kind: MediaKind | None = None
    checkability: Checkability
    entities: list[str] = []
    normalized_claim: str | None = None
    embedded_claims: list[str] = []
    confidence: float = 0.0


def validate_consistency(out: ClassificationOut) -> list[str]:
    """The 4 consistency rules (05 §3.2); [] means valid."""
    errors: list[str] = []
    if (out.claim_kind is not None) != (out.content_type == ContentType.FACTUAL_CLAIM):
        errors.append(
            "claim_kind must be set if and only if content_type is FACTUAL_CLAIM"
            f" (got claim_kind={out.claim_kind} with {out.content_type.value})"
        )
    if (out.media_kind is not None) != (
        out.content_type == ContentType.MEDIA_REFERENCE
    ):
        errors.append(
            "media_kind must be set if and only if content_type is MEDIA_REFERENCE"
            f" (got media_kind={out.media_kind} with {out.content_type.value})"
        )
    if out.checkability == Checkability.NOT_CHECKABLE and (
        out.normalized_claim is not None or out.embedded_claims
    ):
        errors.append(
            "NOT_CHECKABLE means normalized_claim is None and embedded_claims"
            " is empty"
        )
    if (
        out.content_type == ContentType.MEDIA_REFERENCE
        and out.checkability == Checkability.NOT_CHECKABLE
    ):
        errors.append("a MEDIA_REFERENCE is never NOT_CHECKABLE")
    return errors
