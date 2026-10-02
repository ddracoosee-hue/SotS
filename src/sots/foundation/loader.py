"""Foundation loading + validation (P04A T04A.002, 23 §1).

Loads every foundation file into a frozen `Foundation`: the P04 profile
bundle, the anchor registry, the book architecture, parsed briefs (`chNN.yaml`
when present), the style seed, and the verified manuscript. Lenient like the
profile loader: problems accumulate in `errors`, never raise.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from sots.foundation.manuscript import Manuscript, load_manuscript
from sots.models.foundation import (
    Alternative,
    ArchPhase,
    ArcStep,
    BookArchitecture,
    BriefAnchor,
    BriefEdit,
    ChapterBrief,
    MotifSerial,
)
from sots.profile.loader import ProfileBundle, load_profile

#: The original brief numbers, forever (R-FOUND-03).
CHAPTER_IDS = [f"ch{i:02d}" for i in range(1, 13)]

_ANCHOR_ID_RE = re.compile(r"^(ch\d+)\.[A-Z]+\d+$")


class Foundation(BaseModel):
    """Everything a run needs to know about the book (frozen)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile: ProfileBundle
    anchors: list[BriefAnchor]
    architecture: BookArchitecture
    briefs: dict[str, ChapterBrief]
    seed: dict[str, Any]
    manuscript: Manuscript
    errors: list[str]


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    """Parse a YAML file; problems come back as text."""
    if not path.is_file():
        return None, f"{path.name}: file missing"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), None
    except yaml.YAMLError as exc:
        return None, f"{path.name}: cannot parse: {exc}"


def _load_anchors(path: Path) -> tuple[list[BriefAnchor], list[str]]:
    data, problem = _load_yaml(path)
    if problem is not None:
        return [], [problem]
    if not isinstance(data, dict) or not isinstance(data.get("anchors"), list):
        return [], ["anchors.yaml: needs an 'anchors' list"]
    anchors: list[BriefAnchor] = []
    errors: list[str] = []
    for index, entry in enumerate(data["anchors"]):
        where = f"anchors.yaml: entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{where}: not a mapping")
            continue
        try:
            anchor = BriefAnchor.model_validate(entry)
        except ValidationError as exc:
            first = exc.errors()[0]
            errors.append(f"{where}: {first['loc']}: {first['msg']}")
            continue
        match = _ANCHOR_ID_RE.match(anchor.id)
        if match is None:
            errors.append(f"{where}: id {anchor.id!r} is not chNN.<KIND>nn")
            continue
        if match.group(1) not in CHAPTER_IDS:
            errors.append(f"{where}: chapter prefix {match.group(1)!r} out of range")
            continue
        anchors.append(anchor)
    return anchors, errors


def _validate_each(
    filename: str, field: str, model: type[BaseModel], entries: Any
) -> tuple[list[Any], list[str]]:
    """Validate a list of sub-models, collecting per-entry problems."""
    if entries is None:
        return [], []
    if not isinstance(entries, list):
        return [], [f"{filename}: '{field}' must be a list"]
    valid: list[Any] = []
    errors: list[str] = []
    for index, entry in enumerate(entries):
        try:
            valid.append(model.model_validate(entry))
        except ValidationError as exc:
            first = exc.errors()[0]
            errors.append(f"{filename}: {field} {index}: {first['loc']}: {first['msg']}")
    return valid, errors


def _load_architecture(path: Path) -> tuple[BookArchitecture, list[str]]:
    data, problem = _load_yaml(path)
    if problem is not None:
        return BookArchitecture(), [problem]
    if not isinstance(data, dict):
        return BookArchitecture(), ["book_architecture.yaml: must be a mapping"]
    errors: list[str] = []
    reading_order = data.get("reading_order", [])
    if not isinstance(reading_order, list) or [
        c for c in reading_order if isinstance(c, str)
    ] != reading_order:
        errors.append("book_architecture.yaml: 'reading_order' must be a string list")
        reading_order = []
    elif sorted(reading_order) != CHAPTER_IDS:
        errors.append("book_architecture.yaml: 'reading_order' is not a permutation")
    phases, errs = _validate_each(
        "book_architecture.yaml", "phases", ArchPhase, data.get("phases", [])
    )
    errors.extend(errs)
    arc, errs = _validate_each(
        "book_architecture.yaml", "arc", ArcStep, data.get("arc", [])
    )
    errors.extend(errs)
    serials, errs = _validate_each(
        "book_architecture.yaml", "motif_serials", MotifSerial, data.get("motif_serials", [])
    )
    errors.extend(errs)
    edits, errs = _validate_each(
        "book_architecture.yaml", "brief_edits_required", BriefEdit,
        data.get("brief_edits_required", []),
    )
    errors.extend(errs)
    alternatives, errs = _validate_each(
        "book_architecture.yaml", "alternatives", Alternative, data.get("alternatives", [])
    )
    errors.extend(errs)
    known = set(CHAPTER_IDS)
    for phase in phases:
        for chapter in phase.chapters:
            if chapter not in known:
                errors.append(f"book_architecture.yaml: phase {phase.id} has {chapter}")
    for step in arc:
        if step.ch not in known:
            errors.append(f"book_architecture.yaml: arc pos {step.pos} has {step.ch}")
    for serial in serials:
        for chapter in serial.plan:
            if chapter != "all" and chapter not in known:
                errors.append(
                    f"book_architecture.yaml: motif {serial.motif} plans {chapter}"
                )
    for edit in edits:
        if edit.ch not in known:
            errors.append(f"book_architecture.yaml: brief edit for {edit.ch}")
    return BookArchitecture(
        reading_order=list(reading_order), phases=phases, arc=arc,
        motif_serials=serials, brief_edits_required=edits, alternatives=alternatives,
    ), errors


def _load_briefs(chapters_dir: Path) -> tuple[dict[str, ChapterBrief], list[str]]:
    """Parsed `chNN.yaml` briefs (absent = not parsed yet, never an error)."""
    briefs: dict[str, ChapterBrief] = {}
    errors: list[str] = []
    if not chapters_dir.is_dir():
        return briefs, errors
    for path in sorted(chapters_dir.glob("ch*.yaml")):
        data, problem = _load_yaml(path)
        if problem is not None:
            errors.append(problem)
            continue
        try:
            brief = ChapterBrief.model_validate(data)
        except ValidationError as exc:
            first = exc.errors()[0]
            errors.append(f"{path.name}: {first['loc']}: {first['msg']}")
            continue
        if brief.chapter_id != path.stem:
            errors.append(
                f"{path.name}: chapter_id {brief.chapter_id!r} mismatches the filename"
            )
            continue
        briefs[brief.chapter_id] = brief
    return briefs, errors


def _load_seed(path: Path) -> tuple[dict[str, Any], list[str]]:
    data, problem = _load_yaml(path)
    if problem is not None:
        return {}, [problem]
    if not isinstance(data, dict):
        return {}, ["style_guide_seed.yaml: must be a mapping"]
    return dict(data), []


def _message_book_links(messages_path: Path) -> list[str]:
    """Every chapter message's `book:` refs must name real book messages."""
    data, problem = _load_yaml(messages_path)
    if problem is not None or not isinstance(data, dict):
        return []
    if "book" not in data and "chapters" not in data:
        return []
    book_ids = {
        entry.get("id") for entry in data.get("book") or []
        if isinstance(entry, dict)
    }
    chapters = data.get("chapters") or {}
    if not isinstance(chapters, dict):
        return []
    errors: list[str] = []
    for entries in chapters.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            for ref in entry.get("book") or []:
                if ref not in book_ids:
                    errors.append(
                        f"messages.yaml: {entry.get('id')} links unknown book {ref}"
                    )
    return errors


def _range_errors(anchors: list[BriefAnchor], profile: ProfileBundle) -> list[str]:
    """Anchor prefixes, message chapters, and brief ids stay in ch01-ch12."""
    errors: list[str] = []
    for anchor in anchors:
        prefix = anchor.id.split(".")[0]
        if prefix not in CHAPTER_IDS:
            errors.append(f"anchors.yaml: {anchor.id} prefix out of range")
    for message in profile.messages:
        if message.level == "chapter" and message.chapter_id not in CHAPTER_IDS:
            errors.append(f"messages.yaml: {message.id} chapter out of range")
    for entry in profile.chapter_files:
        if entry.chapter_id is not None and entry.chapter_id not in CHAPTER_IDS:
            errors.append(f"chapters/: {entry.path} id out of range")
    return errors


def _manuscript_errors(manuscript: Manuscript) -> list[str]:
    """Author-final chapters must verify; a missing set is not an error."""
    errors: list[str] = []
    for chapter_id in sorted(manuscript.chapters):
        chapter = manuscript.chapters[chapter_id]
        if chapter.expected_sha256 is None:
            errors.append(f"manuscript/{chapter_id}: no expected sha256 in analysis")
        elif not chapter.verified:
            errors.append(f"manuscript/{chapter_id}: sha256 mismatch (must be immutable)")
    return errors


def load_foundation(profile_dir: str | Path) -> Foundation:
    """Load + validate every foundation file (T04A.002)."""
    root = Path(profile_dir)
    profile = load_profile(root)
    anchors, anchor_errors = _load_anchors(root / "anchors.yaml")
    architecture, arch_errors = _load_architecture(root / "book_architecture.yaml")
    briefs, brief_errors = _load_briefs(root / "chapters")
    seed, seed_errors = _load_seed(root / "style_guide_seed.yaml")
    manuscript = load_manuscript(root)
    errors = (
        anchor_errors + arch_errors + brief_errors + seed_errors
        + _message_book_links(root / "messages.yaml")
        + _range_errors(anchors, profile)
        + _manuscript_errors(manuscript)
    )
    return Foundation(
        profile=profile, anchors=anchors, architecture=architecture,
        briefs=briefs, seed=seed, manuscript=manuscript, errors=errors,
    )
