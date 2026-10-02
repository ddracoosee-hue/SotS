"""P00 slice E (T00.050-T00.052): CLI stubs, write exit code, init idempotence."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import yaml
from typer.testing import CliRunner

from sots.cli import app

runner = CliRunner()

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROFILE_DIR = Path(__file__).resolve().parents[2] / "profile"

EXPECTED_TOP_COMMANDS = [
    "init",
    "ingest",
    "run",
    "resume",
    "status",
    "report",
    "claims",
    "expand",
    "audit",
    "eval",
    "cost",
    "tui",
    "write",
    "doctor",
    "stop",
    "act",
    "advance",
    "chapter",
    "style-guide",
    "revisions",
    "hunks",
    "audience",
    "legal",
    "proposals",
    "grader",
    "learning",
    "export",
    "replay",
    "reason",
    "mge",
    "revise",
    "master-audit",
    "voice",
    "profile",
    "settings",
    "vault",
]


def test_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in EXPECTED_TOP_COMMANDS:
        assert command in result.output, f"missing from --help: {command}"


def test_write_exits_2() -> None:
    result = runner.invoke(app, ["write", "chapter one"])
    assert result.exit_code == 2
    assert "Writer is disabled (R-SCOPE-02)" in result.output


def test_write_exits_2_with_no_args() -> None:
    result = runner.invoke(app, ["write"])
    assert result.exit_code == 2
    assert "Writer is disabled (R-SCOPE-02)" in result.output


def test_stub_exits_1_with_phase() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "not yet implemented (phase P13)" in result.output


def test_subcommand_stub_exits_1() -> None:
    result = runner.invoke(app, ["voice", "profile"])
    assert result.exit_code == 1
    assert "not yet implemented (phase P11A)" in result.output


def _snapshot(root: Path) -> dict[str, str]:
    digest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def test_init_creates_tree_and_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    first = runner.invoke(app, ["init"])
    assert first.exit_code == 0, first.output

    for dirname in ("data", "data/inbox", "data/cache", "data/runs", "data/logs", "data/exports"):
        assert (tmp_path / dirname).is_dir(), f"missing dir: {dirname}"
    db = tmp_path / "data/sots.db"
    assert db.is_file()
    assert db.stat().st_size == 0

    expected_files = [
        "profile/author.md",
        "profile/book.md",
        "profile/messages.yaml",
        "profile/chapters/README.md",
        "profile/voice_corpus/README.md",
        "profile/voice_corpus/manifest.yaml",
    ]
    for rel in expected_files:
        assert (tmp_path / rel).is_file(), f"missing template copy: {rel}"
    for register in ("final", "drafts", "spoken", "casual", "pairs", "not_me"):
        assert (tmp_path / "profile/voice_corpus" / register).is_dir()

    # Template headings match the 03 §8 models.
    author = (tmp_path / "profile/author.md").read_text(encoding="utf-8")
    for heading in (
        "Name or Pen Name",
        "Background",
        "Why This Book",
        "Lived Experience Areas",
        "Sensitive Topics",
        "Values",
        "Known Biases",
    ):
        assert heading in author, f"missing author heading: {heading}"
    book = (tmp_path / "profile/book.md").read_text(encoding="utf-8")
    for heading in (
        "Working Title",
        "Genre",
        "Premise",
        "Target Reader",
        "Promise to the Reader",
        "Tone Goals",
        "Out of Scope",
    ):
        assert heading in book, f"missing book heading: {heading}"

    before = _snapshot(tmp_path)
    second = runner.invoke(app, ["init"])
    assert second.exit_code == 0, second.output
    assert _snapshot(tmp_path) == before


def test_init_does_not_overwrite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "profile/author.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("# Mine\n", encoding="utf-8")
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert custom.read_text(encoding="utf-8") == "# Mine\n"


def _fresh_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    settings_path = root / "config" / "settings.yaml"
    raw = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    raw["languagetool"]["url"] = "http://127.0.0.1:1"  # nothing listens here
    settings_path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    (root / "prompts").mkdir()
    (root / "prompts" / "x.v1.md").write_text("---\n{}\n---\nbody\n", encoding="utf-8")
    shutil.copytree(PROMPTS_DIR / "_demo", root / "prompts" / "_demo")
    return root


def test_doctor_command_passes_on_fresh_root(tmp_path: Path) -> None:
    """P03 T03.056: `sots doctor` runs the F17 checks (warnings allowed)."""
    result = runner.invoke(app, ["doctor", "--root", str(_fresh_root(tmp_path))])
    assert result.exit_code == 0, result.output


def test_doctor_command_fails_without_config(tmp_path: Path) -> None:
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path / "empty")])
    assert result.exit_code == 1


def test_stop_command_creates_stop_file(tmp_path: Path) -> None:
    """P03 T03.055: `sots stop` engages the F16 kill switch file."""
    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    result = runner.invoke(app, ["stop", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert (root / "data" / "STOP").is_file()


def _profile_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    return root


INTERVIEW_INPUT = "\n".join([
    "Caleb Crouch", "Philosopher", "To help",
    "addiction", "",
    "family health", "",
    "truth", "",
    "stories over stats", "",
    "The Subject", "",
    "Premise here", "Adults", "Clarity",
    "warm", "",
    "diagnosis", "",
    "reality tv", "",
]) + "\n"  # the final blank line ends the last list


def test_profile_interview_writes_files(tmp_path: Path) -> None:
    """P04 T04.003/T04.005: the interview writes both profile files."""
    from sots.profile.loader import load_profile

    root = _profile_root(tmp_path)
    result = runner.invoke(
        app, ["profile", "interview", "--root", str(root)], input=INTERVIEW_INPUT
    )
    assert result.exit_code == 0, result.output
    bundle = load_profile(root / "profile")
    assert bundle.author is not None
    assert bundle.author.name_or_pen_name == "Caleb Crouch"
    assert bundle.author.lived_experience_areas == ["addiction"]
    assert bundle.book is not None
    assert bundle.book.working_title == "The Subject"
    assert bundle.book.genre == "self_help_reflective"


def test_profile_interview_decline_keeps_files(tmp_path: Path) -> None:
    """P04 T04.003: existing files survive a declined overwrite."""
    root = _profile_root(tmp_path)
    first = runner.invoke(
        app, ["profile", "interview", "--root", str(root)], input=INTERVIEW_INPUT
    )
    assert first.exit_code == 0, first.output
    before = {
        name: (root / "profile" / name).read_bytes()
        for name in ("author.md", "book.md")
    }
    second = runner.invoke(
        app, ["profile", "interview", "--root", str(root)], input="n\nn\n"
    )
    assert second.exit_code == 0, second.output
    for name, content in before.items():
        assert (root / "profile" / name).read_bytes() == content


def test_profile_check_clean_and_dirty(tmp_path: Path) -> None:
    """P04 T04.004/T04.005: `profile check` passes clean, fails dirty."""
    import profile_fixtures as fixtures

    root = _profile_root(tmp_path)
    fixtures.build_full_profile(root)
    clean = runner.invoke(app, ["profile", "check", "--root", str(root)])
    assert clean.exit_code == 0, clean.output
    (root / "profile" / "author.md").write_text("# empty\n", encoding="utf-8")
    dirty = runner.invoke(app, ["profile", "check", "--root", str(root)])
    assert dirty.exit_code == 1
    assert "[error]" in dirty.output


def test_ingest_command_and_duplicates(tmp_path: Path) -> None:
    """P04 T04.014: ingest prints the id; duplicates reuse by default."""
    root = _profile_root(tmp_path)
    source = root / "note.md"
    source.write_text("hello ingest", encoding="utf-8")
    first = runner.invoke(app, ["ingest", str(source), "--root", str(root)])
    assert first.exit_code == 0, first.output
    doc_id = first.output.strip().splitlines()[-1]
    assert doc_id.startswith("doc_")
    assert (root / "data" / "sots.db").is_file()

    reuse = runner.invoke(
        app, ["ingest", str(source), "--root", str(root)], input="y\n"
    )
    assert reuse.exit_code == 0, reuse.output
    assert reuse.output.strip().splitlines()[-1] == doc_id

    forced = runner.invoke(
        app, ["ingest", str(source), "--root", str(root)], input="n\n"
    )
    assert forced.exit_code == 0, forced.output
    assert forced.output.strip().splitlines()[-1] != doc_id

    missing = runner.invoke(
        app, ["ingest", str(root / "nope.md"), "--root", str(root)]
    )
    assert missing.exit_code == 1
    assert "ingest failed" in missing.output


def _foundation_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    profile = root / "profile"
    (profile / "chapters").mkdir(parents=True)
    for name in (
        "anchors.yaml", "book_architecture.yaml", "messages.yaml",
        "style_guide_seed.yaml", "author.md", "book.md",
    ):
        shutil.copy(PROFILE_DIR / name, profile / name)
    return root


def test_foundation_check_passes_and_fails(tmp_path: Path) -> None:
    """P04A T04A.013: `foundation check` validates every foundation file."""
    root = _foundation_root(tmp_path)
    clean = runner.invoke(app, ["foundation", "check", "--root", str(root)])
    assert clean.exit_code == 0, clean.output
    assert "foundation ok" in clean.output
    (root / "profile" / "anchors.yaml").write_text("anchors: nope\n", encoding="utf-8")
    dirty = runner.invoke(app, ["foundation", "check", "--root", str(root)])
    assert dirty.exit_code == 1
    assert "[error]" in dirty.output


def test_foundation_parse_guards(tmp_path: Path) -> None:
    """P04A T04A.012: chapter validation, overwrite guards (no LLM needed)."""
    root = _foundation_root(tmp_path)
    bad = runner.invoke(app, ["foundation", "parse", "ch99", "--root", str(root)])
    assert bad.exit_code == 1
    assert "unknown chapter" in bad.output

    empty = runner.invoke(app, ["foundation", "parse", "all", "--root", str(root)])
    assert empty.exit_code == 1
    assert "no brief files found" in empty.output

    shutil.copy(PROFILE_DIR / "chapters" / "ch01_brief.md", root / "profile" / "chapters")
    yaml_path = root / "profile" / "chapters" / "ch01.yaml"
    yaml_path.write_text("old: true\n", encoding="utf-8")
    skip = runner.invoke(app, ["foundation", "parse", "ch01", "--root", str(root)])
    assert skip.exit_code == 0, skip.output
    assert "use --overwrite" in skip.output
    assert yaml_path.read_text(encoding="utf-8") == "old: true\n"

    decline = runner.invoke(
        app, ["foundation", "parse", "ch01", "--overwrite", "--root", str(root)],
        input="n\n",
    )
    assert decline.exit_code == 0, decline.output
    assert "aborted" in decline.output
    assert yaml_path.read_text(encoding="utf-8") == "old: true\n"


def _review_root(tmp_path: Path) -> Path:
    """Tmp project with config + a seeded review queue (P06 T06.008)."""
    from sots.models.unit import Unit
    from sots.storage import db as storage_db
    from sots.storage import repo as storage_repo

    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    db_path = root / "data" / "sots.db"
    db_path.parent.mkdir(parents=True)
    conn = storage_db.connect(db_path)
    try:
        storage_db.migrate(conn)
        storage_repo.save_unit(conn, Unit(
            id="u-low", document_id="d", chunk_id="c", run_id="r", order=0,
            text="Wobbly words here.", start_char=0, end_char=18,
            content_type="personal_belief", checkability="not_checkable",
            classify_confidence=0.4,
        ))
        storage_repo.save_unit(conn, Unit(
            id="u-high", document_id="d", chunk_id="c", run_id="r", order=1,
            text="Solid words here.", start_char=0, end_char=17,
            content_type="personal_belief", checkability="not_checkable",
            classify_confidence=0.95,
        ))
    finally:
        conn.close()
    return root


def test_review_list_and_relabel(tmp_path: Path) -> None:
    """P06 T06.008: list shows the queue; relabel sticks as author."""
    from sots.models.enums import ContentType
    from sots.storage import db as storage_db
    from sots.storage import repo as storage_repo

    root = _review_root(tmp_path)
    listed = runner.invoke(app, ["review", "list", "--root", str(root)])
    assert listed.exit_code == 0, listed.output
    assert "u-low" in listed.output
    assert "u-high" not in listed.output
    assert "1 unit(s) need review" in listed.output

    relabeled = runner.invoke(app, [
        "review", "relabel", "u-low", "--type", "factual_claim",
        "--claim-kind", "statistic", "--checkability", "checkable",
        "--claim", "Words wobble.", "--root", str(root),
    ])
    assert relabeled.exit_code == 0, relabeled.output
    assert "relabeled u-low as" in relabeled.output

    conn = storage_db.connect(root / "data" / "sots.db")
    try:
        unit = storage_repo.get_unit(conn, "u-low")
        assert unit is not None
        assert unit.content_type == ContentType.FACTUAL_CLAIM
        assert unit.normalized_claim == "Words wobble."
        assert unit.labeled_by == "author"
    finally:
        conn.close()

    again = runner.invoke(app, ["review", "list", "--root", str(root)])
    assert again.exit_code == 0
    assert "0 unit(s) need review" in again.output

    missing = runner.invoke(
        app, ["review", "relabel", "u-nope", "--root", str(root)]
    )
    assert missing.exit_code == 1
    assert "relabel failed" in missing.output
