"""Book Foundation models (P04A T04A.001; blueprint 23 §2, 25 §1).

ChapterBrief here replaces the provisional model in 03 §8. BriefAnchor
carries two fields beyond the 23 §2 sketch (`block`, `serial`) because the
real `anchors.yaml` has them and the loader must accept the real files.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class EpistemicTier(StrEnum):
    """Author-claim tiers (25 §1): fact, theory, or interpretation."""

    DF = "DF"
    PT = "PT"
    IE = "IE"
    DEBUNKED = "DEBUNKED"
    HEDGE = "HEDGE"


class DictationPrompt(BaseModel):
    """One dictation prompt (`ch03.B2.P1`: chapter.block.prompt)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str


class AnchorMedia(BaseModel):
    """Pre-resolved media identity for `media` anchors (23 §3.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    title: str
    year: int | None = None
    creator: str | None = None


class BriefAnchor(BaseModel):
    """One Anchor Registry entry (anchors.yaml + brief linkage)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    type: Literal[
        "research", "statistic", "thinker_framework", "scripture", "patristic",
        "media", "manuscript_quote", "case_study", "composite_case", "protocol",
        "historical",
    ]
    text: str
    claim_kind: str | None = None
    tier_claimed: str | None = None
    reuse: list[str] = []
    preflags: list[str] = []
    legal: list[str] = []
    status: str = "active"
    provenance: str | None = None
    author_decision: str | None = None
    translation_choice: str | None = None
    block: int | None = None
    serial: str | None = None
    media: AnchorMedia | None = None


class Protocol(BaseModel):
    """One book protocol (`ch05.P2`); load auditing fills the time cost."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    steps: str
    evidence_grade_claimed: str | None = None
    evidence_basis_claimed: str | None = None
    time_cost_per_week_min: int | None = None


class Block(BaseModel):
    """One of the 6 micro-architecture blocks (23 §2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: Literal[1, 2, 3, 4, 5, 6]
    name: Literal[
        "hook_targeting", "paradigm_shift", "core_mechanism", "case_study",
        "actionable_implementation", "integration_reflection",
    ]
    structural_purpose: str
    old_belief: str | None = None
    new_belief: str | None = None
    anchors: list[str] = []
    dictation_prompts: list[DictationPrompt] = []
    protocols: list[Protocol] = []
    journaling_prompts: list[str] = []
    tables: list[dict[str, Any]] = []


class ChapterBrief(BaseModel):
    """The structured brief (parsed from `chNN_brief.md` by P04A.010)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str
    title: str
    subtitle: str
    phase_claimed: str | None = None
    core_theme: str
    blocks: list[Block] = []
    voice_rules_from_appendix: list[str] = []
    appendix_system_prompt: str = ""
    raw_brief_path: str = ""
    brief_hash: str = ""


class ArchPhase(BaseModel):
    """One book phase (a movement across chapters)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    chapters: list[str]
    movement: str


class ArcStep(BaseModel):
    """One chapter's role in the reading-order arc."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pos: int
    ch: str
    role: str
    intensity: int


class MotifSerial(BaseModel):
    """Teach-once/call-back plan for a recurring motif."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    motif: str
    plan: dict[str, str] = {}
    ref: str | None = None
    open_to_additions: bool = False


class BriefEdit(BaseModel):
    """One required brief edit (delivered as a proposal, never auto-applied)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ch: str
    edit: str


class Alternative(BaseModel):
    """One alternative chapter ordering the author rejected or shelved."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    order: list[str]
    note: str


class BookArchitecture(BaseModel):
    """Reading order, phases, arc, serials, edits, alternatives (23 §1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reading_order: list[str] = []
    phases: list[ArchPhase] = []
    arc: list[ArcStep] = []
    motif_serials: list[MotifSerial] = []
    brief_edits_required: list[BriefEdit] = []
    alternatives: list[Alternative] = []


class FoundationChange(BaseModel):
    """One versioned foundation change (23 §6: who, what, why, diff)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str
    version: int
    who: str
    what: str
    why: str
    diff: str = ""
    created_at: datetime
