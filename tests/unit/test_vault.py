"""Obsidian-vault mirror tests (OI-42): paths, writer, sync, CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from sots.cli import app
from sots.config import load_settings
from sots.models.run import ChapterState
from sots.models.vault import VaultAuthorNote, VaultFoundation, VaultNote
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo
from sots.vault import dashboard, digest, notes, paths, sync
from sots.vault.writer import (
    GENERATED_END,
    GENERATED_START,
    build_note_text,
    dump_frontmatter,
    extract_author_section,
    split_frontmatter,
    write_note,
)

runner = CliRunner()
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


# --- paths ---


def test_slugify() -> None:
    assert paths.slugify("Provocation Spiral") == "provocation-spiral"
    assert paths.slugify("  Caleb's arc! ") == "caleb-s-arc"
    assert paths.slugify("___") == "untitled"


def test_note_paths_and_stems() -> None:
    assert paths.chapter_note_rel_path("ch01") == "Chapters/ch01 - The Modern Day.md"
    assert paths.chapter_stem("ch01") == "Chapters/ch01 - The Modern Day"
    assert paths.anchor_note_rel_path("ch03.A06") == "Anchors/ch03.A06.md"
    assert paths.message_note_rel_path("C1.1") == "Messages/C1.1.md"
    assert paths.motif_note_rel_path("Caleb's arc") == "Motifs/caleb-s-arc.md"
    assert paths.wikilink("Chapters/ch01 - X", "ch01") == "[[Chapters/ch01 - X|ch01]]"
    assert paths.wikilink("Chapters/ch01 - X") == "[[Chapters/ch01 - X]]"


def test_anchor_owner_and_chapter_ids() -> None:
    assert paths.chapter_id_from_anchor("ch03.A06") == "ch03"
    assert paths.chapter_id_from_anchor("ch01.P2") == "ch01"
    assert paths.chapter_id_from_anchor("bogus") is None
    assert paths.is_chapter_id("ch12")
    assert not paths.is_chapter_id("ch1")
    assert not paths.is_chapter_id("M1")


# --- writer ---


def test_frontmatter_round_trip() -> None:
    frontmatter = {"chapter_id": "ch01", "tags": ["chapter"], "phase": None}
    text = dump_frontmatter(frontmatter) + "\nbody\n"
    data, body = split_frontmatter(text)
    assert data == frontmatter
    assert body == "\nbody\n"


def test_split_frontmatter_missing_or_invalid() -> None:
    assert split_frontmatter("no frontmatter") == ({}, "no frontmatter")
    assert split_frontmatter("---\n[unclosed\n") == ({}, "---\n[unclosed\n")


def test_extract_author_section_variants() -> None:
    assert extract_author_section(None) == ""
    fresh = dump_frontmatter({"a": 1}) + "\nbody without markers\n"
    assert extract_author_section(fresh).startswith("## Author notes")
    authored = (
        "---\nt: 1\n---\n\n"
        f"{GENERATED_START}\ngen\n{GENERATED_END}\n\n"
        "## Author notes\n\nMy words.\n"
    )
    assert extract_author_section(authored) == "## Author notes\n\nMy words.\n"


def test_build_note_preserves_author_notes() -> None:
    note = VaultNote(rel_path="x.md", frontmatter={"k": "v"}, generated_body="gen v2")
    existing = build_note_text(
        VaultNote(rel_path="x.md", frontmatter={"k": "v"}, generated_body="gen v1")
    )
    existing += "Extra line by the author.\n"
    rebuilt = build_note_text(note, existing)
    assert "gen v2" in rebuilt
    assert "Extra line by the author." in rebuilt
    assert rebuilt.count(GENERATED_START) == 1
    assert rebuilt.count(GENERATED_END) == 1


def test_write_note_outcomes(tmp_path: Path) -> None:
    note = VaultNote(rel_path="Chapters/n.md", frontmatter={}, generated_body="g")
    assert write_note(tmp_path, note) == "created"
    assert write_note(tmp_path, note) == "unchanged"
    changed = VaultNote(rel_path="Chapters/n.md", frontmatter={}, generated_body="g2")
    assert write_note(tmp_path, changed) == "updated"


# --- fixtures ---


def _write_profile(profile: Path) -> None:
    (profile / "chapters").mkdir(parents=True)
    (profile / "book.md").write_text("# Book\n", encoding="utf-8")
    (profile / "messages.yaml").write_text(
        yaml.safe_dump(
            {
                "book": [{"id": "M1", "priority": 1, "statement": "Agency matters."}],
                "chapters": {
                    "ch01": [
                        {
                            "id": "C1.1",
                            "priority": 1,
                            "statement": "Feeds farm attention.",
                            "book": ["M1"],
                        }
                    ],
                    "ch03": [
                        {
                            "id": "C3.1",
                            "priority": 1,
                            "statement": "You are the witness.",
                            "book": ["M1"],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (profile / "anchors.yaml").write_text(
        yaml.safe_dump(
            {
                "anchors": [
                    {
                        "id": "ch01.A05",
                        "block": 3,
                        "type": "research",
                        "text": "Wanting vs liking",
                        "claim_kind": "academic_finding",
                        "reuse": ["ch03"],
                        "preflags": ["Label the feed claim IE."],
                    },
                    {
                        "id": "ch03.P2",
                        "block": 5,
                        "type": "protocol",
                        "text": "Circuit breaker",
                        "claim_kind": "evidence_grade",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (profile / "book_architecture.yaml").write_text(
        yaml.safe_dump(
            {
                "status": "order_approved",
                "reading_order": ["ch01", "ch03"],
                "phases": [
                    {"id": "P1", "name": "Trap", "chapters": ["ch01"], "movement": "Dx"}
                ],
                "arc": [{"pos": 1, "ch": "ch01", "role": "Cold open", "intensity": 7}],
                "motif_serials": [
                    {"motif": "Why", "plan": {"ch01": "closing Q", "ch03": "built on it"}}
                ],
                "hard_dependencies": ["ch01 < ch03"],
            }
        ),
        encoding="utf-8",
    )
    (profile / "chapters" / "ch01_brief.md").write_text(
        "CHAPTER 1 BRIEFING:THE MODERN DAY\n", encoding="utf-8"
    )
    (profile / "chapters" / "ch03_brief.md").write_text(
        "CHAPTER 3 TALKING POINTS BRIEF\n", encoding="utf-8"
    )


def test_discover_chapters_unions_sources(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    assert sync.discover_chapters(profile) == ["ch01", "ch03"]


def test_load_foundation_partial_profile(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    foundation = sync.load_foundation(profile)
    assert isinstance(foundation, VaultFoundation)
    assert foundation.chapter_ids == []
    assert foundation.architecture_status == "unknown"


def test_sync_creates_wikilinked_notes(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    vault = tmp_path / "vault"
    counts = sync.sync_foundation(profile, vault)
    # index + dashboard + 2 chapters + 2 anchors + 1 book msg + 2 chapter msgs
    # + motif + order + digest
    assert (counts.created, counts.updated, counts.unchanged) == (12, 0, 0)

    index = (vault / "Book Index.md").read_text(encoding="utf-8")
    assert "[[Chapters/ch01 - The Modern Day|ch01 · The Modern Day]]" in index
    assert "[[Motifs/why|Why]]" in index

    ch01 = (vault / paths.chapter_note_rel_path("ch01")).read_text(encoding="utf-8")
    assert "[[Anchors/ch01.A05|ch01.A05]]" in ch01
    assert "[[Messages/C1.1|C1.1]]" in ch01
    assert "[[Motifs/why|Why]]" in ch01
    # Cross-chapter reuse, both directions of the ch01.A05 -> ch03 link.
    assert "[[Chapters/ch03 - Consciousness|ch03]]" in ch01
    ch03 = (vault / paths.chapter_note_rel_path("ch03")).read_text(encoding="utf-8")
    assert "[[Anchors/ch01.A05|ch01.A05]]" in ch03

    anchor = (vault / "Anchors/ch01.A05.md").read_text(encoding="utf-8")
    assert "Label the feed claim IE." in anchor
    assert "[[Chapters/ch03 - Consciousness|ch03]]" in anchor

    message = (vault / "Messages/M1.md").read_text(encoding="utf-8")
    assert "[[Chapters/ch01 - The Modern Day|ch01]]" in message

    motif = (vault / "Motifs/why.md").read_text(encoding="utf-8")
    assert "[[Chapters/ch01 - The Modern Day|ch01 · The Modern Day]]" in motif

    order = (vault / "Architecture/Reading Order.md").read_text(encoding="utf-8")
    assert "ch01 < ch03" in order

    dash = (vault / "Book Dashboard.md").read_text(encoding="utf-8")
    assert "## Protocol inventory (1 across the book)" in dash
    assert "[[Anchors/ch03.P2|ch03.P2]]" in dash
    assert "[[Anchors/ch01.A05|ch01.A05]]" in dash  # reuse hotspot

    author_digest = (vault / "Author Notes Digest.md").read_text(encoding="utf-8")
    assert "No author notes written yet." in author_digest

    # Obsidian scaffolding exists.
    assert (vault / ".obsidian/app.json").is_file()
    assert (vault / "README.md").is_file()
    assert (vault / ".sots-sync.yaml").is_file()


def test_sync_is_idempotent_and_preserves_authors(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    vault = tmp_path / "vault"
    sync.sync_foundation(profile, vault)

    second = sync.sync_foundation(profile, vault)
    assert (second.created, second.updated, second.unchanged) == (0, 0, 12)

    # Author edits survive a re-sync that also updates generated content.
    # (A comment-only YAML touch would parse identically and correctly update
    # nothing, so the fixture changes a real movement value instead.)
    ch01_path = vault / paths.chapter_note_rel_path("ch01")
    edited = ch01_path.read_text(encoding="utf-8") + "My margin thought.\n"
    ch01_path.write_text(edited, encoding="utf-8")
    arch_path = profile / "book_architecture.yaml"
    arch = yaml.safe_load(arch_path.read_text(encoding="utf-8"))
    arch["phases"][0]["movement"] = "Diagnosis, expanded"
    arch_path.write_text(yaml.safe_dump(arch), encoding="utf-8")
    third = sync.sync_foundation(profile, vault)
    assert third.updated >= 1
    assert "My margin thought." in ch01_path.read_text(encoding="utf-8")


def test_status_detects_stale_and_missing(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    vault = tmp_path / "vault"
    assert sync.vault_status(profile, vault) != []  # never synced: everything stale
    sync.sync_foundation(profile, vault)
    assert sync.vault_status(profile, vault) == []
    (profile / "messages.yaml").write_text("# changed\n", encoding="utf-8")
    stale = sync.vault_status(profile, vault)
    assert [s.path for s in stale] == ["messages.yaml"]
    (profile / "messages.yaml").unlink()
    stale = sync.vault_status(profile, vault)
    assert stale and stale[0].current_hash is None


def test_init_vault_idempotent(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    first = sync.init_vault(vault)
    assert first.created >= 7  # 5 subdirs + README + app.json
    second = sync.init_vault(vault)
    assert (second.created, second.updated) == (0, 0)


def test_note_builders_handle_empty_foundation() -> None:
    foundation = VaultFoundation()
    index = notes.build_book_index(foundation)
    assert "Book Index" in index.generated_body
    chapter = notes.build_chapter_note(foundation, "ch01")
    assert "ch01" in chapter.generated_body
    anchor = notes.build_anchor_note({"id": "ch01.A01"})
    assert "ch01.A01" in anchor.generated_body


# --- config + CLI ---


def test_settings_loads_vault_section() -> None:
    settings = load_settings(CONFIG_DIR, env_file=None)
    assert settings.paths.vault_dir == "data/vault"
    assert settings.vault.enabled is True
    assert settings.vault.author_notes_heading == "## Author notes"
    assert settings.vault.index_note == "Book Index.md"


def test_vault_help_lists_commands() -> None:
    result = runner.invoke(app, ["vault", "--help"])
    assert result.exit_code == 0
    for command in ("init", "sync", "status", "digest"):
        assert command in result.output


def test_vault_cli_sync_and_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.chdir(tmp_path)
    shutil.copytree(CONFIG_DIR, tmp_path / "config")
    _write_profile(tmp_path / "profile")
    synced = runner.invoke(app, ["vault", "sync"])
    assert synced.exit_code == 0, synced.output
    assert "created=" in synced.output
    status = runner.invoke(app, ["vault", "status"])
    assert status.exit_code == 0
    assert "up to date" in status.output


def test_vault_cli_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.chdir(tmp_path)
    shutil.copytree(CONFIG_DIR, tmp_path / "config")
    _write_profile(tmp_path / "profile")
    assert runner.invoke(app, ["vault", "sync"]).exit_code == 0
    ch01 = tmp_path / "data/vault" / paths.chapter_note_rel_path("ch01")
    ch01.write_text(ch01.read_text(encoding="utf-8") + "A margin thought.\n", encoding="utf-8")
    result = runner.invoke(app, ["vault", "digest"])
    assert result.exit_code == 0, result.output
    assert "Author Notes Digest.md" in result.output
    digest_note = (tmp_path / "data/vault" / "Author Notes Digest.md").read_text(
        encoding="utf-8"
    )
    assert "A margin thought." in digest_note


# --- dashboard ---


def test_dashboard_tables(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    body = dashboard.build_dashboard_note(sync.load_foundation(profile)).generated_body
    # Chapters at a glance: pos, phase, msgs, anchors, protocols, motifs, pipeline.
    assert "| 1 | [[Chapters/ch01 - The Modern Day|ch01 · The Modern Day]]" in body
    assert "| P1 | 1 | 1 | 0 | 1 | — |" in body
    assert "| 2 | [[Chapters/ch03 - Consciousness|ch03 · Consciousness]]" in body
    # Protocol inventory, hotspots hottest-first, message coverage with counts.
    assert "## Protocol inventory (1 across the book)" in body
    assert "| [[Anchors/ch01.A05|ch01.A05]] |" in body
    assert "| 1: [[Chapters/ch03 - Consciousness|ch03]] |" in body
    assert "| [[Messages/M1|M1]] | 2:" in body


def test_dashboard_pipeline_cells() -> None:
    foundation = VaultFoundation(
        chapter_ids=["ch01", "ch02"],
        reading_order=["ch01", "ch02"],
        chapter_states={
            "ch01": ChapterState(
                chapter_id="ch01",
                act=3,
                gate_status={"a": "passed", "b": "failed"},
                blocked_reasons=[],
            ),
            "ch02": ChapterState(
                chapter_id="ch02",
                act=4,
                gate_status={"a": "passed"},
                blocked_reasons=["waiver needed"],
            ),
        },
    )
    body = dashboard.build_dashboard_note(foundation).generated_body
    assert "Act 3 · 1/2 gates" in body
    assert "Act 4 · 1/1 gates · BLOCKED (1)" in body


def test_dashboard_empty_foundation() -> None:
    body = dashboard.build_dashboard_note(VaultFoundation()).generated_body
    assert "No chapters yet" in body
    assert "No protocols recorded" in body
    assert "None recorded" in body
    assert "No book messages recorded" in body


# --- pipeline state ---


def test_chapter_note_pipeline_state() -> None:
    with_state = VaultFoundation(
        chapter_ids=["ch01"],
        chapter_states={
            "ch01": ChapterState(
                chapter_id="ch01",
                act=2,
                gate_status={"gate_a": "passed", "legal": "pending"},
                blocked_reasons=["need waiver"],
            )
        },
    )
    body = notes.build_chapter_note(with_state, "ch01").generated_body
    assert "- Act: 2" in body
    assert "gate_a=passed" in body
    assert "- Blocked: need waiver" in body
    bare = notes.build_chapter_note(
        VaultFoundation(chapter_ids=["ch01"]), "ch01"
    ).generated_body
    assert "The pipeline has not run for this chapter yet." in bare


def test_load_chapter_states_missing_db(tmp_path: Path) -> None:
    assert sync.load_chapter_states(tmp_path / "nope.db") == {}
    assert sync.load_chapter_states(None) == {}


def test_load_chapter_states_reads_db(tmp_path: Path) -> None:
    db_path = tmp_path / "s.db"
    conn = storage_db.connect(db_path)
    storage_db.migrate(conn)
    storage_repo.save_chapter_state(
        conn,
        ChapterState(
            chapter_id="ch01", act=2, gate_status={"a": "passed"}, blocked_reasons=[]
        ),
    )
    conn.close()
    states = sync.load_chapter_states(db_path)
    assert states["ch01"].act == 2
    assert states["ch01"].gate_status == {"a": "passed"}


def test_load_chapter_states_corrupt_db_degrades(tmp_path: Path) -> None:
    db_path = tmp_path / "s.db"
    db_path.write_bytes(b"not a database")
    assert sync.load_chapter_states(db_path) == {}


def test_sync_loads_states_from_db(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    db_path = tmp_path / "s.db"
    conn = storage_db.connect(db_path)
    storage_db.migrate(conn)
    storage_repo.save_chapter_state(
        conn, ChapterState(chapter_id="ch01", act=5, gate_status={}, blocked_reasons=[])
    )
    conn.close()
    vault = tmp_path / "vault"
    sync.sync_foundation(profile, vault, db_path=db_path)
    ch01 = (vault / paths.chapter_note_rel_path("ch01")).read_text(encoding="utf-8")
    assert "- Act: 5" in ch01


# --- digest ---


def test_digest_collects_and_skips_placeholders(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    vault = tmp_path / "vault"
    sync.sync_foundation(profile, vault)
    assert digest.collect_author_notes(vault) == []
    ch01 = vault / paths.chapter_note_rel_path("ch01")
    ch01.write_text(
        ch01.read_text(encoding="utf-8") + "Margin thought here.\n", encoding="utf-8"
    )
    entries = digest.collect_author_notes(vault)
    assert len(entries) == 1
    assert "Margin thought here." in entries[0].text
    assert entries[0].rel_path == paths.chapter_note_rel_path("ch01")


def test_digest_excludes_itself(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    _write_profile(profile)
    vault = tmp_path / "vault"
    sync.sync_foundation(profile, vault)
    assert digest.refresh_digest(vault) == "unchanged"  # wrote empty digest on sync
    digest_path = vault / "Author Notes Digest.md"
    digest_path.write_text(
        digest_path.read_text(encoding="utf-8") + "Note to self in the digest.\n",
        encoding="utf-8",
    )
    assert digest.collect_author_notes(vault) == []
    assert digest.refresh_digest(vault) == "unchanged"


def test_digest_truncates_long_entries() -> None:
    note = digest.build_digest_note(
        [VaultAuthorNote(rel_path="Chapters/n.md", text="x" * 3000)]
    )
    assert "…(truncated)" in note.generated_body
    assert note.rel_path == "Author Notes Digest.md"


def test_digest_refresh_outcomes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    assert digest.refresh_digest(vault) == "created"
    assert digest.refresh_digest(vault) == "unchanged"


# --- vault models ---


def test_vault_models_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        VaultNote(rel_path="x", frontmatter={}, generated_body="g", bogus=1)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        VaultFoundation(bogus=True)  # type: ignore[call-arg]
