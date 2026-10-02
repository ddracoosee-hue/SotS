"""P05 stage/summarizer/invariant tests (T05.008-T05.010)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sots.agents.failsafes.f20_invariants import InvariantContext, check_all
from sots.config import load_settings
from sots.models.document import Document
from sots.models.enums import ContentType
from sots.models.unit import Unit
from sots.providers.fake import FakeProvider
from sots.providers.prompts import load_prompt
from sots.providers.router import RoutingConfig, RoutingTask
from sots.segment.chunker import chunk_document
from sots.segment.offsets import UnitSpan
from sots.segment.segment_stage import chunk_id_for, run_segment_stage
from sots.segment.summarizer import fit_words, summarize_document
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"
SENTENCE = "The quick brown fox jumps over the lazy dog near the river bank. "


def _routing() -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={
            "segment.extract_units": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=4000
            ),
            "summarize.chunk": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=800
            ),
        },
    )


def _doc_row(doc_id: str, inbox: Path, text: str) -> Document:
    return Document(
        id=doc_id, source_path=str(inbox / "src.md"),
        inbox_path=str(inbox / "raw.md"), sha256="0" * 64, title="T",
        chapter_id=None, char_count=len(text), word_count=len(text.split()),
        ingested_at=datetime.now(UTC),
    )


def _unit(uid: str, doc: str, text: str, start: int, end: int) -> Unit:
    return Unit(
        id=uid, document_id=doc, chunk_id="c0", run_id="r", order=0,
        text=text, start_char=start, end_char=end,
    )


async def test_stage_end_to_end(tmp_path: Path) -> None:
    """T05.008: one chunk in, ordered persisted units + checkpoint out."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    text = "Alpha here. Beta here."
    (inbox / "doc1.txt").write_text(text, encoding="utf-8")
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("segment.extract_units", [
            {"text": json.dumps({"units": [
                {"text": "Alpha here.", "start": 0, "end": 11},
                {"text": "Beta here.", "start": 12, "end": 22},
            ]})},
        ])
        units = await run_segment_stage(
            "doc1", run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, inbox_dir=inbox, prompts_dir=PROMPTS_DIR,
        )
        assert [(u.text, u.order) for u in units] == [
            ("Alpha here.", 0), ("Beta here.", 1),
        ]
        assert all(text[u.start_char:u.end_char] == u.text for u in units)
        assert len(storage_repo.list_chunks(conn, document_id="doc1")) == 1
        assert storage_repo.get_checkpoint(conn, chunk_id_for("doc1", 0)) is not None
    finally:
        conn.close()


async def test_resume_skips_completed_chunks(tmp_path: Path) -> None:
    """T05.008: checkpointed chunks reuse spans; the provider never sees them."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    para0 = "MARKERZERO. " + SENTENCE * 200
    para1 = "MARKERONE. Small tail paragraph here."
    text = f"{para0}\n\n{para1}"
    (inbox / "doc1.txt").write_text(text, encoding="utf-8")
    settings = load_settings(CONFIG_DIR, env_file=None)
    target = settings.chunk.target_tokens.local
    spans = chunk_document(text, target, settings.chunk.overlap_tokens)
    assert len(spans) == 2
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        chunk0 = text[spans[0].start_char:spans[0].end_char]
        storage_repo.save_checkpoint(conn, chunk_id_for("doc1", 0), {
            "spans": [UnitSpan(text=chunk0, start=0, end=len(chunk0)).model_dump()],
        }, run_id="r0")
        chunk1 = text[spans[1].start_char:spans[1].end_char]
        fake = FakeProvider()
        fake.script_default("segment.extract_units", [
            {"text": json.dumps({"units": [
                {"text": chunk1, "start": 0, "end": len(chunk1)},
            ]})},
        ])
        units = await run_segment_stage(
            "doc1", run_id="r1", conn=conn, settings=settings, routing=_routing(),
            providers={"fake": fake}, inbox_dir=inbox, prompts_dir=PROMPTS_DIR,
        )
        bodies = [c.messages[0]["content"] for c in fake.calls]
        assert bodies, "expected extraction calls for the pending chunk"
        assert all("MARKERZERO" not in body for body in bodies)
        assert any("MARKERONE" in body for body in bodies)
        assert units[0].text == chunk0  # checkpoint spans lead, in order
        assert any("MARKERONE" in u.text for u in units)
    finally:
        conn.close()


async def test_dropped_units_log_and_fall_back(tmp_path: Path) -> None:
    """T05.005/006: paraphrases drop, log, and fall back to NARRATIVE_DEVICE."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    text = "Real words the model will paraphrase away."
    (inbox / "doc1.txt").write_text(text, encoding="utf-8")
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("segment.extract_units", [
            {"text": json.dumps({"units": [
                {"text": "Completely unrelated invented sentence here.", "start": 0, "end": 5},
            ]})},
        ])
        units = await run_segment_stage(
            "doc1", run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, inbox_dir=inbox, prompts_dir=PROMPTS_DIR,
        )
        events = storage_repo.list_events(conn, run_id="r1")
        assert any(e["type"] == "segment.unmatched_unit" for e in events)
        assert len(units) == 1
        assert units[0].content_type == ContentType.NARRATIVE_DEVICE
        assert units[0].classify_confidence == 0.0
        assert units[0].text == text
    finally:
        conn.close()


def test_summarize_prompt_and_fit() -> None:
    """T05.009: prompt front-matter + the 200-word guarantee."""
    prompt = load_prompt(PROMPTS_DIR, "summarize/summarize_chunk", 1)
    assert prompt.output_model == "ChunkSummaryOut"
    assert set(prompt.variables) == {"level", "text"}
    assert "200 words" in prompt.body
    assert len(fit_words("w " * 250).split()) == 200
    assert fit_words("short") == "short"


async def test_summary_tree_shapes(tmp_path: Path) -> None:
    """T05.009: 1/7/8/9/65 chunks roll up to exactly one root."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("summarize.chunk", [{"text": json.dumps(
            {"text": "A fine summary of the chunk content."})}]),
        kwargs = dict(
            run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        )
        for count, expected in (
            (1, [1]), (7, [7, 1]), (8, [8, 1]), (9, [9, 2, 1]), (65, [65, 9, 2, 1]),
        ):
            doc = f"doc{count}"
            chunks = [(f"c{i}", f"Chunk {i} says words about the river bank fox.")
                      for i in range(count)]
            tree = await summarize_document(doc, chunks, **kwargs)
            assert tree.level_counts == expected, count
            root = storage_repo.get_summary(conn, tree.root_id)
            assert root is not None and root["body"]["level"] == len(expected) - 1
            rows = storage_repo.list_summaries(conn, document_id=doc)
            assert len(rows) == sum(expected)
    finally:
        conn.close()


def test_offset_integrity_invariant(tmp_path: Path) -> None:
    """T05.010: text mismatches and bad offsets are violations."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    text = "Alpha here. Beta here."
    (inbox / "doc1.txt").write_text(text, encoding="utf-8")
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        storage_repo.save_document(conn, _doc_row("doc1", inbox, text))
        storage_repo.save_unit(conn, _unit("u-good", "doc1", "Alpha here.", 0, 11))
        storage_repo.save_unit(conn, _unit("u-bad", "doc1", "WRONG TEXT!", 12, 22))
        storage_repo.save_unit(conn, _unit("u-oob", "doc1", "Beta here.", 12, 999))
        report = check_all(InvariantContext(root=tmp_path, conn=conn))
        violations = report["offset_integrity"]
        assert len(violations) == 2
        assert any("u-bad" in v and "mismatch" in v for v in violations)
        assert any("u-oob" in v and "outside" in v for v in violations)
    finally:
        conn.close()
