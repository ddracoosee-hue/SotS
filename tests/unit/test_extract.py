"""P05 extractor/offset/coverage/dedup tests (T05.003-T05.007)."""

from __future__ import annotations

import json
from pathlib import Path

from sots.config import load_settings
from sots.models.enums import ContentType
from sots.providers.fake import FakeProvider
from sots.providers.prompts import load_prompt
from sots.providers.router import RoutingConfig, RoutingTask
from sots.segment.coverage import cover_chunk, coverage_ratio
from sots.segment.dedup import DedupCandidate, dedupe
from sots.segment.extractor import RawUnit, extract_chunk
from sots.segment.offsets import UnitSpan, repair_units
from sots.storage import db as storage_db

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"


def test_prompt_front_matter() -> None:
    """T05.003: the extract prompt loads with its ruler + examples."""
    prompt = load_prompt(PROMPTS_DIR, "segment/extract_units", 1)
    assert prompt.output_model == "ExtractUnitsOut"
    assert set(prompt.variables) == {"chunk_start", "chunk_text"}
    assert "relative to the chunk" in prompt.body
    assert "Divorce rates" in prompt.body and "Dad sang off-key" in prompt.body
    rendered = prompt.render({"chunk_start": "120", "chunk_text": "Hi."})
    assert "120" in rendered and "Hi." in rendered


async def test_extract_chunk_fake(tmp_path: Path) -> None:
    """T05.004: one chunk through the FakeProvider."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("segment.extract_units", [
            {"text": json.dumps({"units": [
                {"text": "Alpha.", "start": 0, "end": 6},
                {"text": "Beta beta.", "start": 7, "end": 17},
            ]})},
        ])
        routing = RoutingConfig(
            fallback_order=[],
            tasks={"segment.extract_units": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=4000
            )},
        )
        units = await extract_chunk(
            "c0", "Alpha. Beta beta.", 0, run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=routing,
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        )
        assert [(u.text, u.start, u.end) for u in units] == [
            ("Alpha.", 0, 6), ("Beta beta.", 7, 17),
        ]
        assert "Alpha. Beta beta." in fake.calls[0].messages[0]["content"]
    finally:
        conn.close()


def test_repair_steps() -> None:
    """T05.005: exact, shifted, paraphrase-drop, duplicate-first-unused."""
    chunk = "Alpha here. Beta here. Alpha here."
    out = repair_units(chunk, [
        RawUnit(text="Alpha here.", start=0, end=11),       # step 1: exact
        RawUnit(text="Beta here.", start=99, end=109),      # step 2: shifted
        RawUnit(text="Gamma never appears here.", start=0, end=5),  # drop
        RawUnit(text="Alpha here.", start=50, end=61),      # dup: 2nd occurrence
        RawUnit(text="Alpha here.", start=51, end=62),      # dup: all used
    ])
    assert [(s.text, s.start, s.end) for s in out.repaired] == [
        ("Alpha here.", 0, 11),
        ("Beta here.", 12, 22),
        ("Alpha here.", 23, 34),
    ]
    assert [u.text for u in out.dropped] == [
        "Gamma never appears here.", "Alpha here.",
    ]
    for span in out.repaired:
        assert chunk[span.start:span.end] == span.text


def test_repair_fuzzy_adopts_substring() -> None:
    """T05.005 step 3: near-miss aligns and the text is replaced."""
    chunk = "The quick brown fox jumps."
    raw = RawUnit(text="The quick brown fox jumpz.", start=0, end=1)
    out = repair_units(chunk, [raw])
    assert out.dropped == []
    (span,) = out.repaired
    assert span.text != raw.text  # replaced with the actual substring
    assert chunk[span.start:span.end] == span.text == "The quick brown fox jumps."


async def test_coverage_backstop() -> None:
    """T05.006: gap re-extracts once, then NARRATIVE_DEVICE covers all."""
    chunk = "Covered words here. Lost words there."

    async def reextract(text: str, base: int) -> list[RawUnit]:
        assert (text, base) == ("Lost words there.", 20)
        return []  # the model finds nothing: fallback must cover it

    spans = [UnitSpan(text="Covered words here.", start=0, end=19)]
    assert coverage_ratio(chunk, spans) < 0.85
    covered = await cover_chunk(chunk, spans, reextract)
    assert coverage_ratio(chunk, covered) == 1.0
    fallback = [s for s in covered if s.content_type is not None]
    assert len(fallback) == 1
    assert fallback[0].content_type == ContentType.NARRATIVE_DEVICE
    assert fallback[0].classify_confidence == 0.0


async def test_coverage_reextract_repairs() -> None:
    """T05.006: a productive re-extract lands translated, no fallback."""
    chunk = "Covered words here. Found words there."

    async def reextract(text: str, base: int) -> list[RawUnit]:
        assert base == 20
        return [RawUnit(text=text, start=0, end=len(text))]

    covered = await cover_chunk(
        chunk, [UnitSpan(text="Covered words here.", start=0, end=19)], reextract
    )
    assert coverage_ratio(chunk, covered) == 1.0
    assert all(s.content_type is None for s in covered)
    assert (covered[1].start, covered[1].end) == (20, 38)


def test_dedupe_earlier_chunk_wins() -> None:
    """T05.007: overlapping ≥90-similar spans keep the earlier chunk."""
    kept = dedupe([
        DedupCandidate(text="The shared overlap sentence.", start_char=90,
                       end_char=118, chunk_index=1),
        DedupCandidate(text="The shared overlap sentence.", start_char=90,
                       end_char=118, chunk_index=0),
        DedupCandidate(text="Something entirely different here.", start_char=10,
                       end_char=44, chunk_index=1),
    ])
    assert [(c.chunk_index, c.text) for c in kept] == [
        (0, "The shared overlap sentence."),
        (1, "Something entirely different here."),
    ]
