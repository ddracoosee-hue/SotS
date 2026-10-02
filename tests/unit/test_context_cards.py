"""P04A context-card tests (T04A.014, T04A.020-T04A.022, 23 §3)."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

import sots.agents.tools  # noqa: F401 (register every tool)
from sots.agents.cards import cards_missing_foundation
from sots.agents.failsafes.f17_doctor import run_doctor
from sots.config import load_settings
from sots.foundation.anchors import AnchorRegistry
from sots.foundation.architecture import Architecture
from sots.foundation.cards import (
    CARD_BUDGETS,
    f1_book_card,
    f2_chapter_card,
    f3_block_card,
    f4_anchor_card,
    f5_voice_card,
    f6_arc_card,
)
from sots.foundation.loader import CHAPTER_IDS, load_foundation
from sots.models.foundation import Block, ChapterBrief
from sots.providers.context_pack import (
    NON_CONTENT_TASKS,
    PIECE_TITLES,
    TASK_PIECES,
    ContextSources,
    PieceInput,
    build,
    render,
)
from sots.providers.fake import FakeProvider
from sots.providers.router import load_routing

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"
PROFILE_DIR = ROOT / "profile"


def _counter(text: str) -> int:
    return FakeProvider().count_tokens(text)


def _brief(chapter_id: str, registry: AnchorRegistry) -> ChapterBrief:
    """A small but structurally complete brief for card testing."""
    first = registry.by_chapter(chapter_id)
    anchor = first[0].id if first else f"{chapter_id}.A99"
    names = [
        "hook_targeting", "paradigm_shift", "core_mechanism", "case_study",
        "actionable_implementation", "integration_reflection",
    ]
    blocks = [
        Block.model_validate({
            "number": number, "name": name,
            "structural_purpose": f"Purpose of {name} in {chapter_id}.",
            "old_belief": "Old." if number == 2 else None,
            "new_belief": "New." if number == 2 else None,
            "anchors": [anchor],
            "dictation_prompts": [
                {"id": f"{chapter_id}.B{number}.P1", "text": "Write it."}
            ],
            "protocols": [],
            "journaling_prompts": [],
            "tables": [],
        })
        for number, name in enumerate(names, start=1)
    ]
    return ChapterBrief(
        chapter_id=chapter_id, title="T", subtitle="S", core_theme=f"Theme of {chapter_id}.",
        blocks=blocks, appendix_system_prompt=f"APPENDIX-SENTINEL-{chapter_id}",
    )


def test_every_card_within_budget_12x6() -> None:
    """T04A.020: F1-F6 within their 23 §3 budgets for all 12x6."""
    foundation = load_foundation(PROFILE_DIR)
    assert foundation.errors == []
    registry = AnchorRegistry(foundation.anchors)
    arch = Architecture(foundation.architecture)
    book_text = (PROFILE_DIR / "book.md").read_text(encoding="utf-8")
    checked = 0
    for chapter_id in CHAPTER_IDS:
        brief = _brief(chapter_id, registry)
        chapter_messages = [
            m for m in foundation.profile.messages
            if m.level == "book" or m.chapter_id == chapter_id
        ]
        for block_number in range(1, 7):
            cards = {
                "f1_book": f1_book_card(book_text, foundation.architecture, _counter),
                "f2_chapter": f2_chapter_card(brief, chapter_messages, _counter),
                "f3_block": f3_block_card(brief, block_number, registry, _counter),
                "f4_anchors": f4_anchor_card(
                    registry, [brief.core_theme, brief.blocks[block_number - 1].name],
                    _counter,
                ),
                "f5_voice": f5_voice_card(foundation.seed, _counter),
                "f6_arc": f6_arc_card(arch, chapter_id, _counter),
            }
            for name, text in cards.items():
                assert _counter(text) <= CARD_BUDGETS[name], (chapter_id, block_number, name)
                checked += 1
    assert checked == 12 * 6 * 6


def test_cards_carry_real_content() -> None:
    foundation = load_foundation(PROFILE_DIR)
    registry = AnchorRegistry(foundation.anchors)
    brief = _brief("ch01", registry)
    book_text = (PROFILE_DIR / "book.md").read_text(encoding="utf-8")
    assert "F1" in f1_book_card(book_text, foundation.architecture, _counter)
    f2 = f2_chapter_card(brief, foundation.profile.messages, _counter)
    assert "Theme of ch01" in f2 and "M1" in f2
    f3 = f3_block_card(brief, 1, registry, _counter)
    assert "hook_targeting" in f3
    assert "ch01.A" in f4_anchor_card(registry, ["Berridge showed wanting"], _counter)
    f5 = f5_voice_card(foundation.seed, _counter, scope_text="the shell and chrestos")
    assert "Protected terms" in f5
    assert "shell" in f5.lower()
    f6 = f6_arc_card(Architecture(foundation.architecture), "ch01", _counter)
    assert "position 1 of 12" in f6


def test_appendix_never_in_cards() -> None:
    """T04A.014 (R-FOUND-04): appendix text cannot leak into any card."""
    foundation = load_foundation(PROFILE_DIR)
    registry = AnchorRegistry(foundation.anchors)
    brief = _brief("ch01", registry)
    assert "APPENDIX-SENTINEL-ch01" in brief.appendix_system_prompt
    book_text = (PROFILE_DIR / "book.md").read_text(encoding="utf-8")
    texts = [
        f1_book_card(book_text, foundation.architecture, _counter),
        f2_chapter_card(brief, foundation.profile.messages, _counter),
        f3_block_card(brief, 2, registry, _counter),
        f4_anchor_card(registry, ["Berridge"], _counter),
        f5_voice_card(foundation.seed, _counter),
        f6_arc_card(Architecture(foundation.architecture), "ch01", _counter),
    ]
    assert all("APPENDIX-SENTINEL-ch01" not in text for text in texts)


def test_task_pieces_enforce_f1_f2() -> None:
    """T04A.021: R-FOUND-01 — every content task loads F1+F2 first."""
    routing = load_routing(CONFIG_DIR / "routing.yaml")
    assert len(routing.tasks) >= 60
    for task in routing.tasks:
        assert task in TASK_PIECES, task
        if task not in NON_CONTENT_TASKS:
            assert TASK_PIECES[task][:2] == ["f1_book", "f2_chapter"], task
    assert frozenset({"learning.summarize"}) == NON_CONTENT_TASKS
    for name in ("f1_book", "f2_chapter", "f3_block", "f4_anchors", "f5_voice", "f6_arc"):
        assert name in PIECE_TITLES
        assert name in ContextSources.model_fields
    settings = load_settings(CONFIG_DIR, env_file=None)
    budgets = settings.context.budgets
    assert (budgets.f1_book, budgets.f2_chapter, budgets.f3_block) == (400, 700, 600)
    assert (budgets.f4_anchors, budgets.f5_voice, budgets.f6_arc) == (800, 500, 300)
    pack = build(
        "classify.unit",
        ContextSources(f1_book=PieceInput(text="book card here")),
        budgets=budgets, context_window=32000, counter=_counter,
    )
    assert "book card here" in render(pack)


def test_foundation_pieces_field_and_doctor_warn(tmp_path: Path) -> None:
    """T04A.022: the card field validates; omissions warn (never fail)."""
    foundation = load_foundation(PROFILE_DIR)
    assert foundation.errors == []

    root = tmp_path / "proj"
    shutil.copytree(CONFIG_DIR, root / "config")
    demo = root / "config" / "agents" / "_demo" / "demo_agent.yaml"
    card = yaml.safe_load(demo.read_text(encoding="utf-8"))
    assert card["foundation_pieces"] == ["F1", "F2"]
    del card["foundation_pieces"]
    demo.write_text(yaml.safe_dump(card), encoding="utf-8")

    (root / "prompts").mkdir()
    (root / "prompts" / "x.v1.md").write_text("---\n{}\n---\nbody\n", encoding="utf-8")
    shutil.copytree(PROMPTS_DIR / "_demo", root / "prompts" / "_demo")
    import asyncio

    report = asyncio.run(run_doctor(root))
    by_name = {check.name: check for check in report.checks}
    assert by_name["cards"].status == "warn"
    assert "R-FOUND-01" in by_name["cards"].detail
    assert report.failed is False


def test_cards_missing_foundation_helper() -> None:
    from sots.agents.cards import load_cards
    from sots.agents.tools.base import registered_tools

    cards = load_cards(
        CONFIG_DIR / "agents",
        prompts_dir=PROMPTS_DIR,
        routing=load_routing(CONFIG_DIR / "routing.yaml"),
        tools=registered_tools(),
    )
    assert cards_missing_foundation(cards) == []
