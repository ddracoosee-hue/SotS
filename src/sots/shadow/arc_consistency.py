"""Arc consistency checks (P04A T04A.042, 23 §7).

Phase labels, capstone/epilogue/climax claims, "Chapter N of M" counts, and
forward/backward chapter references against the architecture. "Keep '…'"
brief edits approve specific language per chapter.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from sots.foundation.architecture import Architecture

#: Self-labels only: "Book Phase: Phase N", "(Phase N: Name)", "Phase N <Name>".
_LABEL_RES = [
    re.compile(
        r"(?:book\s+|macro-architecture\s+)?phase:\s*phase\s+(\d+)", re.IGNORECASE
    ),
    re.compile(r"\(phase\s+(\d+)\s*:", re.IGNORECASE),
    re.compile(r"^phase\s+(\d+)\s+[A-Z]", re.IGNORECASE | re.MULTILINE),
]
_MULTI_PHASE_RE = re.compile(r"\b[Pp]hase\s+\d+\s*&")
_CAPSTONE_RE = re.compile(r"\b(capstone|epilogue|climax|climactic)\w*\b", re.IGNORECASE)
#: Same-line context that makes a capstone word a structural claim.
_STRUCT_FWD_RE = re.compile(r"of the (entire )?(book|manuscript)|\bchapter\b")
_STRUCT_BACK_RE = re.compile(r"phase|book|manuscript|chapter")
_COUNT_RE = re.compile(r"\b[Cc]hapter\s+(\d+)\s+of\s+(\d+)\b")
_CHAPTER_REF_RE = re.compile(r"\b[Cc]hapter\s+(\d+)\b")
_KEEP_RE = re.compile(r"[Kk]eep\s+'([^']+)'")
_BACKWARD_RE = re.compile(
    r"\b(as we saw|as (?:discussed|shown)|recall(?:ed|s)?(?: from)?)\b[^.]{0,80}?"
    r"\bchapter\s+(\d+)\b",
    re.IGNORECASE,
)
_FORWARD_RE = re.compile(
    r"\b(will see|later in|upcoming in)\b[^.]{0,80}?\bchapter\s+(\d+)\b",
    re.IGNORECASE,
)

IssueKind = Literal["phase_label", "capstone_claim", "chapter_count", "forward_ref"]


class ArcIssue(BaseModel):
    """One arc contradiction with what the architecture expects."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter: str
    kind: IssueKind
    text: str
    expected: str


def _keep_words(architecture: Architecture, chapter_id: str) -> set[str]:
    """Concept words the brief edits explicitly keep for this chapter."""
    words: set[str] = set()
    for edit in architecture.brief_edits:
        if edit.ch != chapter_id:
            continue
        for kept in _KEEP_RE.findall(edit.edit):
            words.update(w for w in re.findall(r"[a-z]+", kept.lower()) if len(w) >= 4)
    return words


def check_arc(
    chapter_id: str, brief_text: str, architecture: Architecture,
    *, total_chapters: int = 12,
) -> list[ArcIssue]:
    """Phase/capstone/count/reference checks for one brief (23 §7)."""
    issues: list[ArcIssue] = []
    own_number = int(chapter_id[2:]) if chapter_id.startswith("ch") else None

    phase = architecture.phase(chapter_id)
    if phase is not None and _MULTI_PHASE_RE.search(brief_text) is None:
        acceptable = {phase.id}
        if phase.id == "EP":
            # Epilogue-phase chapters close the final numbered phase (ch08: Phase 4).
            numbered = [p.id for p in architecture.phases if p.id.startswith("P")]
            if numbered:
                acceptable.add(max(numbered, key=lambda pid: int(pid[1:])))
        for label_re in _LABEL_RES:
            match = label_re.search(brief_text)
            if match is not None and f"P{match.group(1)}" not in acceptable:
                issues.append(ArcIssue(
                    chapter=chapter_id, kind="phase_label",
                    text=f"claims Phase {match.group(1)}",
                    expected=f"architecture phase {phase.id}",
                ))
                break

    approved = _keep_words(architecture, chapter_id)
    for match in _CAPSTONE_RE.finditer(brief_text):
        if match.group(1).lower() in approved:
            continue
        fwd = brief_text[match.end():match.end() + 45].split("\n")[0].lower()
        back = brief_text[max(0, match.start() - 30):match.start()].split("\n")[-1].lower()
        if _STRUCT_FWD_RE.search(fwd) is None and _STRUCT_BACK_RE.search(back) is None:
            continue  # scene-level word ("the climax of <film>"), not a book claim
        issues.append(ArcIssue(
            chapter=chapter_id, kind="capstone_claim",
            text=f"claims {match.group(0)!r}",
            expected="no capstone/epilogue/climax claim (or a Keep edit)",
        ))
        break

    for match in _COUNT_RE.finditer(brief_text):
        number, total = int(match.group(1)), int(match.group(2))
        if total != total_chapters:
            issues.append(ArcIssue(
                chapter=chapter_id, kind="chapter_count",
                text=f"Chapter {number} of {total}",
                expected=f"Chapter {number} of {total_chapters}",
            ))
        elif own_number is not None and number != own_number:
            issues.append(ArcIssue(
                chapter=chapter_id, kind="chapter_count",
                text=f"Chapter {number} of {total}",
                expected=f"chapter number {own_number}",
            ))

    try:
        own_position = architecture.position(chapter_id)
    except ValueError:
        own_position = None
    if own_position is not None:
        order = architecture.reading_order
        for match in _BACKWARD_RE.finditer(brief_text):
            ref = f"ch{int(match.group(2)):02d}"
            if ref in order and order.index(ref) > own_position:
                issues.append(ArcIssue(
                    chapter=chapter_id, kind="forward_ref",
                    text=f"backward reference to {ref}",
                    expected=f"{ref} reads after {chapter_id}",
                ))
        for match in _FORWARD_RE.finditer(brief_text):
            ref = f"ch{int(match.group(2)):02d}"
            if ref in order and order.index(ref) < own_position:
                issues.append(ArcIssue(
                    chapter=chapter_id, kind="forward_ref",
                    text=f"forward reference to {ref}",
                    expected=f"{ref} reads before {chapter_id}",
                ))
    return issues
