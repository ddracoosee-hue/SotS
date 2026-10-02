"""P04A foundation tests: models, loader, registry, architecture, versions."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sots.foundation.anchors import AnchorRegistry, normalize
from sots.foundation.architecture import Architecture
from sots.foundation.loader import CHAPTER_IDS, load_foundation
from sots.foundation.manuscript import load_manuscript
from sots.foundation.versioning import (
    FileVersion,
    detect_changes,
    file_version,
    foundation_versions,
    record_change,
    run_snapshot,
)
from sots.models.foundation import (
    Block,
    BookArchitecture,
    BriefAnchor,
    ChapterBrief,
    DictationPrompt,
    EpistemicTier,
    FoundationChange,
    Protocol,
)

PROFILE_DIR = Path(__file__).resolve().parents[2] / "profile"


def _anchor(anchor_id: str = "ch01.A01", **overrides) -> BriefAnchor:
    base: dict = {"id": anchor_id, "type": "research", "text": "Some finding."}
    base.update(overrides)
    return BriefAnchor.model_validate(base)


def test_model_round_trips() -> None:
    """T04A.001: every foundation model dumps and reloads."""
    assert EpistemicTier("DF") is EpistemicTier.DF
    assert [tier.value for tier in EpistemicTier] == ["DF", "PT", "IE", "DEBUNKED", "HEDGE"]
    prompt = DictationPrompt(id="ch03.B2.P1", text="Write.")
    assert DictationPrompt.model_validate(prompt.model_dump()) == prompt
    anchor = _anchor(
        "ch01.A05", text="Incentive-Salience (Berridge & Robinson).",
        claim_kind="academic_finding", reuse=["ch03"], block=3,
    )
    assert BriefAnchor.model_validate(anchor.model_dump()) == anchor
    protocol = Protocol(id="ch05.P2", name="Sleep", steps="Do it.")
    assert Protocol.model_validate(protocol.model_dump()) == protocol
    block = Block(
        number=2, name="paradigm_shift", structural_purpose="Flip.",
        old_belief="old", new_belief="new", anchors=["ch01.A05"],
        dictation_prompts=[prompt], protocols=[protocol],
        journaling_prompts=["Q?"], tables=[{"a": 1}],
    )
    assert Block.model_validate(block.model_dump()) == block
    brief = ChapterBrief(
        chapter_id="ch01", title="T", subtitle="S", core_theme="C",
        blocks=[block], appendix_system_prompt="sys", raw_brief_path="p", brief_hash="h",
    )
    assert ChapterBrief.model_validate(brief.model_dump()) == brief
    change = FoundationChange(
        file="anchors.yaml", version=1, who="author", what="added",
        why="needed", created_at=datetime.now(UTC),
    )
    assert FoundationChange.model_validate(change.model_dump()) == change
    arch = BookArchitecture(reading_order=["ch01"])
    assert BookArchitecture.model_validate(arch.model_dump()) == arch


def test_real_foundation_loads_clean() -> None:
    """T04A.002: the real profile files load with 0 errors."""
    foundation = load_foundation(PROFILE_DIR)
    assert foundation.errors == []
    assert len(foundation.anchors) == 158
    assert foundation.architecture.reading_order == [
        "ch01", "ch02", "ch03", "ch04", "ch05", "ch07",
        "ch10", "ch11", "ch09", "ch06", "ch12", "ch08",
    ]
    assert foundation.seed["version"] == 1


def test_loader_reports_problems(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    (profile / "chapters").mkdir(parents=True)
    (profile / "anchors.yaml").write_text(
        "anchors:\n  - {id: ch99.A1, type: nope, text: x}\n", encoding="utf-8"
    )
    (profile / "book_architecture.yaml").write_text(
        "reading_order: [ch01, ch01]\n", encoding="utf-8"
    )
    (profile / "messages.yaml").write_text(
        "book:\n  - {id: M1, priority: 1, statement: s}\n"
        "chapters:\n  ch01:\n    - {id: C1.1, priority: 1, statement: s, book: [MX]}\n",
        encoding="utf-8",
    )
    (profile / "style_guide_seed.yaml").write_text("protected_terms: []\n", encoding="utf-8")
    foundation = load_foundation(profile)
    assert any("anchors.yaml" in error for error in foundation.errors)
    assert any("permutation" in error for error in foundation.errors)
    assert any("unknown book MX" in error for error in foundation.errors)


def test_anchor_registry_queries() -> None:
    """T04A.003: by_chapter/by_type/hotspots over the real 158 anchors."""
    registry = AnchorRegistry(load_foundation(PROFILE_DIR).anchors)
    assert len(registry) == 158
    assert registry.by_id("ch01.A05") is not None
    assert registry.by_id("ch99.A1") is None
    assert {a.id for a in registry.by_chapter("ch01")} >= {"ch01.A05"}
    assert all(a.id.startswith("ch01.") for a in registry.by_chapter("ch01"))
    assert all(a.type == "protocol" for a in registry.by_type("protocol"))
    hotspots = registry.reuse_hotspots()
    assert hotspots and all(a.reuse for a in hotspots)
    counts = [len(a.reuse) for a in hotspots]
    assert counts == sorted(counts, reverse=True)


def test_anchor_match_in_text() -> None:
    """T04A.003: entity + keyword matching, macrons normalized."""
    registry = AnchorRegistry(load_foundation(PROFILE_DIR).anchors)
    assert "ch01.A05" in registry.match_in_text("Berridge showed wanting beats liking")
    assert "ch05.A04" in registry.match_in_text("like Love Yourz says")
    assert "ch07.A02" in registry.match_in_text("the chrēstos yoke")
    assert "ch07.A02" in registry.match_in_text("the chrestos yoke")
    assert registry.match_in_text("the weather is temperate and mild today") == []
    assert registry.match_in_text("") == []
    assert normalize("chrēstos") == "chrestos"


def test_architecture_queries() -> None:
    """T04A.004: position/phase/arc/callback/motif-plan over the real file."""
    arch = Architecture(load_foundation(PROFILE_DIR).architecture)
    assert arch.position("ch01") == 0
    assert arch.position("ch11") == 7
    assert arch.position("ch08") == 11
    phase = arch.phase("ch02")
    assert phase is not None and phase.id == "P2"
    step = arch.arc_step("ch06")
    assert step is not None and step.pos == 10
    assert step.role.startswith("Outward turn")
    assert arch.arc_position("ch06") == 10
    assert arch.arc_position("ch99") is None
    assert arch.callback_label("ch01") == "Chapter 1"
    assert arch.callback_label("ch11") == "Chapter 8"
    assert arch.callback_label("ch08") == "Chapter 12"
    assert arch.is_callback("J. Cole", "ch05") is False
    assert arch.is_callback("Harvard Study", "ch08") is True
    assert arch.is_callback("Berridge & Robinson", "ch01") is False
    assert arch.is_callback("Kohut", "ch01") is None
    assert arch.is_callback("nope", "ch05") is None
    assert arch.motif_plan("Kohut")["ch07"] != ""
    assert arch.motif_plan("nope") == {}


def test_versioning_helpers(tmp_path: Path) -> None:
    """T04A.005: versions, change records, run snapshots."""
    root = tmp_path / "profile"
    root.mkdir()
    (root / "anchors.yaml").write_text("version: 2\nanchors: []\n", encoding="utf-8")
    (root / "author.md").write_text("hi", encoding="utf-8")
    before = foundation_versions(root)
    assert before["anchors.yaml"].version == 2
    assert len(before["author.md"].sha256) == 64
    (root / "anchors.yaml").write_text("version: 3\nanchors: []\n", encoding="utf-8")
    after = foundation_versions(root)
    changes = detect_changes(before, after, who="author", why="more anchors")
    assert len(changes) == 1
    assert changes[0].what == "version 2 -> 3"
    assert changes[0].who == "author"
    assert file_version(root / "missing.yaml").sha256 == ""
    snapshot = run_snapshot("r1", after)
    assert snapshot.run_id == "r1"
    assert snapshot.versions["anchors.yaml"].startswith("3:")

    added = record_change("x", old=None, new=FileVersion(file="x", version=1, sha256="s"),
                          who="w", why="y")
    assert added.what == "added" and added.version == 1
    removed = record_change("x", old=FileVersion(file="x", version=4, sha256="s"), new=None,
                            who="w", why="y")
    assert removed.what == "removed" and removed.version == 4


def test_manuscript_verification() -> None:
    """T04A.035: the Ch1 hash matches ch01_analysis.md."""
    manuscript = load_manuscript(PROFILE_DIR)
    assert manuscript.reference_chapter == "ch01"
    chapter = manuscript.chapters["ch01"]
    assert chapter.expected_sha256 is not None
    assert chapter.verified is True
    assert chapter.is_reference is True


def test_chapter_ids_constant() -> None:
    assert [f"ch{i:02d}" for i in range(1, 13)] == CHAPTER_IDS
