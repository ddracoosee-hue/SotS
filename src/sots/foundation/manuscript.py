"""Manuscript loading + verification (P04A T04A.035, 23 §1).

Each `chNN_*.md` chapter (analysis files excluded) is hashed and compared
with its `chNN_analysis.md` sibling; ch01 is the reference chapter and the
primary style exemplar.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

_CHAPTER_RE = re.compile(r"^(ch\d{2})_.+\.md$")
_SHA_RE = re.compile(r"\b[0-9a-f]{64}\b")


class ManuscriptChapter(BaseModel):
    """One author-final manuscript chapter + its verification outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str
    path: str
    section: Literal["author_final"] = "author_final"
    text: str
    sha256: str
    expected_sha256: str | None
    verified: bool
    is_reference: bool


class Manuscript(BaseModel):
    """The verified manuscript set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapters: dict[str, ManuscriptChapter]
    reference_chapter: str | None

    @property
    def reference_text(self) -> str:
        """The reference chapter's text (the primary style exemplar)."""
        if self.reference_chapter is None:
            return ""
        chapter = self.chapters.get(self.reference_chapter)
        return chapter.text if chapter is not None else ""


def load_manuscript(
    profile_dir: str | Path, *, reference_chapter: str = "ch01"
) -> Manuscript:
    """Hash every manuscript chapter; verify against its analysis sibling."""
    manuscript = Path(profile_dir) / "manuscript"
    chapters: dict[str, ManuscriptChapter] = {}
    if manuscript.is_dir():
        for path in sorted(manuscript.glob("ch*.md")):
            if path.name.endswith("_analysis.md"):
                continue
            match = _CHAPTER_RE.match(path.name)
            if match is None:
                continue
            chapter_id = match.group(1)
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            analysis = manuscript / f"{chapter_id}_analysis.md"
            expected: str | None = None
            if analysis.is_file():
                found = _SHA_RE.search(analysis.read_text(encoding="utf-8"))
                expected = found.group(0) if found else None
            chapters[chapter_id] = ManuscriptChapter(
                chapter_id=chapter_id,
                path=str(path),
                text=raw.decode("utf-8", errors="replace"),
                sha256=digest,
                expected_sha256=expected,
                verified=expected is not None and expected == digest,
                is_reference=chapter_id == reference_chapter,
            )
    reference = reference_chapter if reference_chapter in chapters else None
    return Manuscript(chapters=chapters, reference_chapter=reference)
