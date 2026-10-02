"""Teach-once/call-back repetition checks (P04A T04A.041, 23 §7).

Compares each chapter's claimed treatment of a reuse hotspot against the
motif serial plan: full treatments where the plan says callback (and the
reverse) are violations. Treatment extraction from text is later-phase
work; this module checks claimed treatments.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from sots.foundation.architecture import Architecture

Treatment = Literal["full", "callback"]


class TreatmentClaim(BaseModel):
    """How one chapter treats one motif (extracted upstream)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    motif: str
    chapter: str
    treatment: Treatment


class RepetitionIssue(BaseModel):
    """A treatment that contradicts the serial plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    motif: str
    chapter: str
    expected: Treatment
    claimed: Treatment


def check_repetition(
    claims: list[TreatmentClaim], architecture: Architecture
) -> list[RepetitionIssue]:
    """Flag treatments that contradict the motif serial plans (23 §7)."""
    issues: list[RepetitionIssue] = []
    for claim in claims:
        planned_callback = architecture.is_callback(claim.motif, claim.chapter)
        if planned_callback is None:
            continue  # unplanned motif/chapter: nothing to contradict
        expected: Treatment = "callback" if planned_callback else "full"
        if expected != claim.treatment:
            issues.append(RepetitionIssue(
                motif=claim.motif, chapter=claim.chapter,
                expected=expected, claimed=claim.treatment,
            ))
    return issues
