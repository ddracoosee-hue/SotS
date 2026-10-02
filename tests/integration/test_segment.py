"""P05 Stage 2 integration (T05.011): fixtures end to end with wrong offsets.

A FakeProvider subclass answers extraction with shifted offsets plus one
paraphrase per chunk, so the run exercises repair, coverage fallback, dedup,
persistence, the summary tree, and the offset_integrity invariant for real.
"""

from __future__ import annotations

import json
from pathlib import Path

from sots.agents.failsafes.f20_invariants import InvariantContext, check_all
from sots.config import load_settings
from sots.ingest.ingest import ingest_file
from sots.providers.base import LLMRequest, LLMResponse
from sots.providers.fake import FakeProvider
from sots.providers.router import RoutingConfig, RoutingTask
from sots.segment.coverage import coverage_ratio
from sots.segment.offsets import UnitSpan
from sots.segment.segment_stage import canonical_text, run_segment_stage
from sots.segment.sentences import split_sentences
from sots.segment.summarizer import summarize_document
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"
FIXTURES = ROOT / "tests" / "fixtures" / "docs"

PARAPHRASE = "Xyzzq plugh invented nonsense wobble quark fidgit widget."


class ShiftingFake(FakeProvider):
    """Extraction answers with +7 shifted offsets and one paraphrase."""

    async def complete(self, req: LLMRequest) -> LLMResponse:
        if req.task != "segment.extract_units":
            return await super().complete(req)
        content = req.messages[0]["content"]
        chunk = content.split("Chunk:\n", 1)[1]
        units = [
            {"text": chunk[s:e], "start": s + 7, "end": e + 7}
            for s, e in split_sentences(chunk)
        ]
        units.append({"text": PARAPHRASE, "start": 0, "end": 5})
        text = json.dumps({"units": units})
        return LLMResponse(
            text=text, input_tokens=0, output_tokens=len(text) // 4,
            model="fake", raw={"task": req.task},
        )


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


async def _run_fixture(
    name: str, inbox: Path, tmp_path: Path, lo: int, hi: int | None,
) -> None:
    fixture = FIXTURES / f"{name}.md"
    assert fixture.is_file()
    words = len(fixture.read_text(encoding="utf-8").split())
    assert words >= lo and (hi is None or words <= hi), (name, words)
    conn = storage_db.connect(tmp_path / f"{name}.db")
    storage_db.migrate(conn)
    try:
        outcome = ingest_file(fixture, conn=conn, inbox_dir=inbox, title=name)
        doc_id = outcome.document.id
        text = canonical_text(inbox, doc_id)
        fake = ShiftingFake()
        fake.script_default("summarize.chunk", [
            {"text": json.dumps({"text": "A fine summary."})},
        ])
        settings = load_settings(CONFIG_DIR, env_file=None)
        kwargs = dict(
            run_id="r1", conn=conn, settings=settings, routing=_routing(),
            providers={"fake": fake}, inbox_dir=inbox, prompts_dir=PROMPTS_DIR,
        )
        units = await run_segment_stage(doc_id, **kwargs)
        assert units
        assert [u.order for u in units] == list(range(len(units)))
        assert all(text[u.start_char:u.end_char] == u.text for u in units)
        assert [u.start_char for u in units] == sorted(u.start_char for u in units)
        doc_spans = [
            UnitSpan(text=u.text, start=u.start_char, end=u.end_char) for u in units
        ]
        assert coverage_ratio(text, doc_spans) == 1.0
        report = check_all(InvariantContext(root=tmp_path, conn=conn))
        assert report["offset_integrity"] == []
        events = storage_repo.list_events(conn, run_id="r1")
        assert any(e["type"] == "segment.unmatched_unit" for e in events)
        chunks = storage_repo.list_chunks(conn, document_id=doc_id)
        assert chunks
        tree = await summarize_document(
            doc_id,
            [(c.id, text[c.start_char:c.end_char]) for c in chunks],
            run_id="r1", conn=conn, settings=settings, routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        )
        assert tree.level_counts[-1] == 1
        assert storage_repo.get_summary(conn, tree.root_id) is not None
    finally:
        conn.close()


async def test_short_fixture(tmp_path: Path) -> None:
    """T05.011: the 1k-word doc segments, covers, and summarizes."""
    await _run_fixture("short", tmp_path / "inbox", tmp_path, 900, 1200)


async def test_medium_fixture(tmp_path: Path) -> None:
    """T05.011: the 8k-word doc segments, covers, and summarizes."""
    await _run_fixture("medium", tmp_path / "inbox", tmp_path, 7000, 9000)


async def test_long_fixture(tmp_path: Path) -> None:
    """T05.011: the >50k-word doc segments, covers, and summarizes."""
    await _run_fixture("long", tmp_path / "inbox", tmp_path, 50000, None)
