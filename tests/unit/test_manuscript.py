"""P04A manuscript tests (T04A.035, 23 §1)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sots.foundation.loader import load_foundation
from sots.foundation.manuscript import load_manuscript

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "profile"


def test_ch01_verifies_and_is_reference() -> None:
    """T04A.035: the Ch1 hash matches ch01_analysis.md; ch01 is reference."""
    manuscript = load_manuscript(PROFILE_DIR)
    assert manuscript.reference_chapter == "ch01"
    ch01 = manuscript.chapters["ch01"]
    assert ch01.sha256 == ch01.expected_sha256
    assert ch01.verified is True
    assert ch01.is_reference is True
    assert ch01.section == "author_final"
    assert "Casey Simpson" in ch01.text
    assert manuscript.reference_text == ch01.text


def test_foundation_wires_manuscript_clean() -> None:
    """The real profile loads with the manuscript and 0 errors."""
    foundation = load_foundation(PROFILE_DIR)
    assert foundation.manuscript.reference_chapter == "ch01"
    assert foundation.errors == []


def _write_chapter(root: Path, body: str, analysis: str) -> None:
    manuscript = root / "manuscript"
    manuscript.mkdir()
    (manuscript / "ch01_test.md").write_text(body, encoding="utf-8", newline="\n")
    (manuscript / "ch01_analysis.md").write_text(analysis, encoding="utf-8")


def test_tampered_chapter_fails_verification(tmp_path: Path) -> None:
    """A sha mismatch verifies False and surfaces a loader error."""
    body = "Author-final words.\n"
    _write_chapter(tmp_path, body, "sha: " + "0" * 64)
    manuscript = load_manuscript(tmp_path)
    assert manuscript.chapters["ch01"].verified is False
    foundation = load_foundation(tmp_path)
    assert "manuscript/ch01: sha256 mismatch (must be immutable)" in foundation.errors


def test_missing_hash_is_an_error(tmp_path: Path) -> None:
    """A chapter with no expected sha cannot be verified."""
    _write_chapter(tmp_path, "Words.\n", "no hash recorded here")
    foundation = load_foundation(tmp_path)
    assert "manuscript/ch01: no expected sha256 in analysis" in foundation.errors


def test_missing_manuscript_dir_is_empty_not_error(tmp_path: Path) -> None:
    """No manuscript received yet: empty set, no reference, lenient."""
    manuscript = load_manuscript(tmp_path)
    assert manuscript.chapters == {}
    assert manuscript.reference_chapter is None
    assert manuscript.reference_text == ""
    foundation = load_foundation(tmp_path)
    assert not [e for e in foundation.errors if e.startswith("manuscript/")]


def test_matching_hash_verifies(tmp_path: Path) -> None:
    """A fixture chapter with the recorded hash verifies True."""
    body = "Author-final words.\n"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    _write_chapter(tmp_path, body, f"recorded sha: {digest}")
    chapter = load_manuscript(tmp_path).chapters["ch01"]
    assert (chapter.expected_sha256, chapter.verified) == (digest, True)
