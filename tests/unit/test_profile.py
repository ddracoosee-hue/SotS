"""P04 profile tests (T04.001-T04.002 loader/hash, T04.004 check)."""

from __future__ import annotations

from pathlib import Path

import profile_fixtures as fixtures

from sots.profile.loader import load_profile, profile_hash
from sots.profile.validate import check_profile


def test_full_profile_loads(tmp_path: Path) -> None:
    """T04.001: every part loads to its typed model."""
    bundle = load_profile(fixtures.build_full_profile(tmp_path))
    assert bundle.missing == []
    assert bundle.author is not None and bundle.author.name_or_pen_name == "Caleb Crouch"
    assert bundle.author.lived_experience_areas == ["addiction and recovery", "rehab"]
    assert bundle.book is not None and bundle.book.genre == "self_help_reflective"
    assert bundle.book.media_exclusions == ["reality-TV retellings"]
    assert [(m.id, m.level, m.chapter_id) for m in bundle.messages] == [
        ("M1", "book", None), ("C1.1", "chapter", "ch01"),
    ]
    assert bundle.voice is not None and len(bundle.voice.samples) == 3
    assert bundle.voice.samples[0].voice_register == "final"
    assert [(f.chapter_id) for f in bundle.chapter_files] == ["ch01"]


def test_partial_profile_lists_missing(tmp_path: Path) -> None:
    """T04.001: a partial profile reports every missing part, never raises."""
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / "author.md").write_text(
        "# Author Profile\n\n## Name or Pen Name\n\nCaleb Crouch\n", encoding="utf-8"
    )
    bundle = load_profile(profile)
    assert bundle.author is None
    assert any("Background" in item for item in bundle.missing)
    assert any("book.md: file missing" in item for item in bundle.missing)
    assert any("messages.yaml: file missing" in item for item in bundle.missing)
    assert any("manifest.yaml: file missing" in item for item in bundle.missing)
    assert any("chapters/" in item for item in bundle.missing)


def test_nested_messages_shape(tmp_path: Path) -> None:
    """T04.001: the draft-v0 nested shape converts; bad entries are reported."""
    profile = fixtures.build_full_profile(tmp_path)
    (profile / "messages.yaml").write_text(
        fixtures.NESTED_MESSAGES + "  ch02:\n    - {id: BAD, statement: 7}\n",
        encoding="utf-8",
    )
    bundle = load_profile(profile)
    assert [(m.id, m.level, m.chapter_id) for m in bundle.messages] == [
        ("M1", "book", None), ("C1.1", "chapter", "ch01"),
    ]
    assert any("BAD" in item for item in bundle.missing)


def test_template_placeholders_are_not_data(tmp_path: Path) -> None:
    """T04.001: example lines and HTML comments never become field values."""
    profile = fixtures.build_full_profile(tmp_path)
    (profile / "author.md").write_text(
        "# Author Profile\n\n<!-- a comment -->\n\n## Name or Pen Name\n\n"
        "Caleb Crouch\n\n## Background\n\n<!-- fill me -->\n\n"
        "## Why This Book\n\nWhy.\n\n## Lived Experience Areas\n\n"
        "- _(example: addiction and recovery)_\n\n## Sensitive Topics\n\n"
        "- _(none yet)_\n\n## Values\n\n- truth\n\n"
        "## Known Biases (self-reported)\n\n- bias\n",
        encoding="utf-8",
    )
    bundle = load_profile(profile)
    assert bundle.author is None
    assert any("Background" in item for item in bundle.missing)
    assert any("Lived Experience Areas" in item for item in bundle.missing)
    assert any("Sensitive Topics" in item for item in bundle.missing)


def test_genre_must_match(tmp_path: Path) -> None:
    profile = fixtures.build_full_profile(tmp_path)
    (profile / "book.md").write_text(
        (profile / "book.md").read_text(encoding="utf-8").replace(
            "self_help_reflective", "memoir"
        ),
        encoding="utf-8",
    )
    bundle = load_profile(profile)
    assert bundle.book is None
    assert any("Genre" in item for item in bundle.missing)


def test_profile_hash_changes(tmp_path: Path) -> None:
    """T04.002: any content/add/remove change moves the hash."""
    profile = fixtures.build_full_profile(tmp_path)
    first = profile_hash(profile)
    assert profile_hash(profile) == first
    (profile / "author.md").write_text(
        (profile / "author.md").read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    assert profile_hash(profile) != first
    added = profile_hash(profile)
    (profile / "chapters" / "ch02_brief.md").write_text("# b", encoding="utf-8")
    assert profile_hash(profile) != added
    (profile / "messages.yaml").unlink()
    assert profile_hash(profile) not in (first, added)


def test_check_profile_clean(tmp_path: Path) -> None:
    """T04.004: a full profile passes (journeys unchecked without P04A yamls)."""
    report = check_profile(fixtures.build_full_profile(tmp_path))
    assert report.ok
    assert report.errors() == [] and report.warnings() == []
    assert any("journeys" in f.message for f in report.findings)


def test_check_profile_problems(tmp_path: Path) -> None:
    """T04.004: bad refs error; uncovered briefs and few samples warn."""
    profile = fixtures.build_full_profile(tmp_path)
    (profile / "messages.yaml").write_text(
        "messages:\n"
        "  - {id: C9.9, level: chapter, chapter_id: ch99,"
        ' statement: "lost", priority: 1}\n',
        encoding="utf-8",
    )
    (profile / "chapters" / "ch02_brief.md").write_text("# b", encoding="utf-8")
    (profile / "voice_corpus" / "final" / "b.md").unlink()
    (profile / "voice_corpus" / "final" / "c.md").unlink()
    (profile / "chapters" / "ch01.yaml").write_text(
        "reader_journey: see ch02 and ch99\n", encoding="utf-8"
    )
    report = check_profile(profile)
    assert not report.ok
    assert any("ch99" in error for error in report.errors())
    assert any("ch01.yaml" in error and "ch99" in error for error in report.errors())
    assert any("ch02" in warn and "no messages" in warn for warn in report.warnings())
    assert any("samples" in warn for warn in report.warnings())
