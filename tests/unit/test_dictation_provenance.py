"""P04A dictation/provenance tests (T04A.030-T04A.032, T04A.034, 23 §5, 25 §7)."""

from __future__ import annotations

import json
from pathlib import Path

from sots.classify.anchors_in_units import tag_anchors
from sots.classify.block_map import map_block
from sots.classify.provenance import classify_provenance
from sots.config import load_settings
from sots.errors import ValidationFailedError
from sots.foundation.anchors import AnchorRegistry
from sots.foundation.loader import load_foundation
from sots.ingest.dictation import parse_keyed_sections
from sots.ingest.provenance_markers import detect_markers
from sots.models.foundation import Block, ChapterBrief
from sots.providers.fake import FakeProvider
from sots.providers.router import RoutingConfig, RoutingTask
from sots.storage import db as storage_db

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"
PROFILE_DIR = ROOT / "profile"


def test_all_five_markers_and_unmarked() -> None:
    """T04A.030: header styles, ### full, [short], and unmarked tail."""
    text = (
        "chapter: ch03\n"
        "block: 2\n"
        "prompt: ch03.B2.P1\n"
        "\n"
        "Header-keyed opening.\n"
        "\n"
        "### ch03.B4.P2\n"
        "\n"
        "Full-marked body.\n"
        "\n"
        "[B5.P1]\n"
        "\n"
        "Short-marked body.\n"
    )
    sections = parse_keyed_sections(text)
    assert [(s.prompt_id, s.chapter_id, s.block) for s in sections] == [
        ("ch03.B2.P1", "ch03", 2),
        ("ch03.B4.P2", "ch03", 4),
        ("ch03.B5.P1", "ch03", 5),
    ]
    for section in sections:
        assert text[section.start_char:section.end_char] == section.text
    assert sections[0].text == "Header-keyed opening."

    unmarked = parse_keyed_sections("Just words.\n\nMore words.\n")
    assert len(unmarked) == 1
    assert unmarked[0].prompt_id is None and unmarked[0].text == "Just words.\n\nMore words."


def test_offsets_exact() -> None:
    sections = parse_keyed_sections("### ch03.B1.P1\n\nHello.\n")
    assert len(sections) == 1
    assert (sections[0].start_char, sections[0].end_char) == (16, 22)
    assert sections[0].text == "Hello."


def test_short_marker_needs_a_chapter() -> None:
    """A [Bn.Pm] marker without chapter context stays literal text."""
    sections = parse_keyed_sections("[B2.P1]\n\nBody.\n")
    assert len(sections) == 1
    assert sections[0].prompt_id is None
    assert "[B2.P1]" in sections[0].text

    sections = parse_keyed_sections("[B2.P1]\n\nBody.\n", default_chapter="ch03")
    assert sections[0].prompt_id == "ch03.B2.P1"
    assert sections[0].text == "Body."


def _brief() -> ChapterBrief:
    return ChapterBrief(
        chapter_id="ch03", title="T", subtitle="S", core_theme="C",
        blocks=[
            Block.model_validate({
                "number": 1, "name": "hook_targeting", "structural_purpose": "Hook.",
                "dictation_prompts": [{"id": "ch03.B1.P1", "text": "Hook it."}],
            }),
            Block.model_validate({
                "number": 2, "name": "paradigm_shift", "structural_purpose": "Flip.",
                "old_belief": "o", "new_belief": "n",
                "dictation_prompts": [{"id": "ch03.B2.P1", "text": "Flip it."}],
            }),
        ],
    )


def _routing() -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={
            "classify.block_map": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=200
            )
        },
    )


async def test_block_map(tmp_path: Path) -> None:
    """T04A.031: unmarked text maps to block/prompt; bad ids rejected."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("classify.block_map", [
            {"text": json.dumps({"block": 2, "prompt_id": "ch03.B2.P1", "confidence": 0.9})},
        ])
        settings = load_settings(CONFIG_DIR, env_file=None)
        kwargs = dict(
            run_id="r1", conn=conn, settings=settings, routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        )
        mapped = await map_block("flip words", "ch03", _brief(), **kwargs)
        assert (mapped.block, mapped.prompt_id) == (2, "ch03.B2.P1")

        fake.script_default("classify.block_map", [
            {"text": json.dumps({"block": 2, "prompt_id": "ch03.B9.P9", "confidence": 0.5})},
        ])
        try:
            # Distinct inputs: call_structured caches by input hash.
            await map_block("bad prompt id", "ch03", _brief(), **kwargs)
            raise AssertionError("expected ValidationFailedError")
        except ValidationFailedError as exc:
            assert "unknown prompt" in str(exc)

        fake.script_default("classify.block_map", [
            {"text": json.dumps({"block": 1, "prompt_id": "ch03.B2.P1", "confidence": 0.5})},
        ])
        try:
            await map_block("wrong block", "ch03", _brief(), **kwargs)
            raise AssertionError("expected ValidationFailedError")
        except ValidationFailedError as exc:
            assert "not in block" in str(exc)
    finally:
        conn.close()


def test_tag_anchors_spans_chapters() -> None:
    """T04A.032: reuse anchors match across chapters."""
    registry = AnchorRegistry(load_foundation(PROFILE_DIR).anchors)
    assert tag_anchors("Berridge showed wanting beats liking", registry) == [
        "ch01.A05", "ch03.A07",
    ]


def test_explicit_markers() -> None:
    """T04A.034: [LIVE]/[SOURCE]/[BELIEF]/[EXPERIENCE]/[OPINION]/[SPIRAL]."""
    hit = detect_markers("Saw it [LIVE: The Atlantic, March 2025] today.")
    assert hit is not None
    assert (hit.provenance, hit.source_ref) == ("live_source", "The Atlantic, March 2025")
    hit = detect_markers("X [SOURCE: creator Y] y.")
    assert hit is not None and hit.provenance == "live_source"
    assert detect_markers("I hold this [BELIEF] deeply.").provenance == "belief"
    assert detect_markers("As a kid [MEMORY] I ran.").provenance == "experience"
    assert detect_markers("He failed [OPINION] utterly.").provenance == "opinion"
    assert detect_markers("Plain text.") is None

    spiral = detect_markers("A loop [SPIRAL] forms.")
    assert spiral is not None and spiral.serial == "provocation_spiral"
    assert spiral.provenance is None
    both = detect_markers("[BELIEF] a loop [SPIRAL] forms.")
    assert both is not None and both.provenance == "belief"
    assert both.serial == "provocation_spiral"

    first_wins = detect_markers("[OPINION] one [BELIEF] two.")
    assert first_wins is not None and first_wins.provenance == "opinion"


def test_provenance_cues_and_review() -> None:
    """T04A.034: NL cues with confidence; markers beat cues."""
    live = classify_provenance("I saw this on the evening news last night.")
    assert live.provenance == "live_source" and live.needs_review is True
    assert live.source_ref == "the evening news last night"
    belief = classify_provenance("I believe grace precedes effort.")
    assert (belief.provenance, belief.needs_review) == ("belief", False)
    assert belief.confidence == 0.8
    exp = classify_provenance("I remember the hospital hallway.")
    assert (exp.provenance, exp.needs_review) == ("experience", True)
    marked = classify_provenance(
        "I believe x [OPINION].", markers=detect_markers("I believe x [OPINION].")
    )
    assert (marked.provenance, marked.confidence) == ("opinion", 1.0)
    assert marked.needs_review is False
    none = classify_provenance("The sky is blue.")
    assert (none.provenance, none.confidence, none.needs_review) == (None, 0.0, False)


def test_ch01_passages() -> None:
    """T04A.034: the §4 opinion paragraph, the belief line, Casey Simpson."""
    opinion = classify_provenance(
        "What follows is my personal opinion. It isn't a finding; "
        "I'd welcome a study that proves me wrong."
    )
    assert (opinion.provenance, opinion.needs_review) == ("opinion", False)
    assert opinion.confidence == 0.9
    belief = classify_provenance("I believe God exists.")
    assert (belief.provenance, belief.needs_review) == ("belief", False)
    chapter = (PROFILE_DIR / "manuscript" / "ch01_the_modern_day.md").read_text(
        encoding="utf-8"
    )
    sentence = next(
        s for s in chapter.replace("\n", " ").split(". ") if "Casey Simpson" in s
    )
    live = classify_provenance(sentence)
    assert live.provenance == "live_source"
    assert live.needs_review is True
    assert live.source_ref is not None and "Casey Simpson" in live.source_ref
