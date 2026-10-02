"""Protocol Load Auditor deterministic core (P04A T04A.040, 23 §7).

Takes per-protocol weekly minutes (LLM estimates + author overrides arrive
with the agent) and checks the cumulative load in reading order against the
book's protocol budget. Findings go to the Shadow Self.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sots.foundation.architecture import Architecture

#: The book's protocol budget (23 §7): few active, few hours.
MAX_ACTIVE_PROTOCOLS = 3
MAX_MINUTES_PER_WEEK = 180


class ProtocolLoadInput(BaseModel):
    """One protocol's weekly cost (estimate or author override)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    chapter: str
    minutes_per_week: int
    active: bool = True


class ChapterLoad(BaseModel):
    """Cumulative load standing at one reading-order chapter."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter: str
    minutes: int
    cumulative_minutes: int
    active_count: int


class ProtocolLoadReport(BaseModel):
    """Whole-book load verdict + per-chapter cumulative table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_min_per_week: int
    active_count: int
    over_budget: bool
    by_chapter: list[ChapterLoad]
    findings: list[str]


def audit_protocol_load(
    protocols: list[ProtocolLoadInput],
    architecture: Architecture,
    *,
    max_active: int = MAX_ACTIVE_PROTOCOLS,
    max_min_per_week: int = MAX_MINUTES_PER_WEEK,
) -> ProtocolLoadReport:
    """Cumulative load in reading order vs the protocol budget (23 §7)."""
    active = [p for p in protocols if p.active]
    total = sum(p.minutes_per_week for p in active)
    by_chapter: list[ChapterLoad] = []
    cumulative = 0
    for chapter in architecture.reading_order:
        mine = [p for p in active if p.chapter == chapter]
        minutes = sum(p.minutes_per_week for p in mine)
        cumulative += minutes
        by_chapter.append(ChapterLoad(
            chapter=chapter, minutes=minutes,
            cumulative_minutes=cumulative, active_count=len(mine),
        ))
    over_budget = len(active) > max_active or total > max_min_per_week
    findings: list[str] = []
    if len(active) > max_active:
        findings.append(
            f"{len(active)} active protocols exceed the <={max_active} start-here budget"
        )
    if total > max_min_per_week:
        findings.append(
            f"{total / 60:.1f} h/week exceeds the <={max_min_per_week // 60}h budget"
        )
    if by_chapter:
        hottest = max(by_chapter, key=lambda c: c.minutes)
        if hottest.minutes > 0:
            findings.append(
                f"heaviest chapter: {hottest.chapter} at {hottest.minutes} min/week"
            )
    return ProtocolLoadReport(
        total_min_per_week=total, active_count=len(active),
        over_budget=over_budget, by_chapter=by_chapter, findings=findings,
    )
