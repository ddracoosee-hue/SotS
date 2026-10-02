"""P06 stage/review/stats/children tests (T06.005-T06.007, T06.009)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sots.agents.failsafes.f20_invariants import InvariantContext, check_all
from sots.classify.classify_stage import run_classify_stage
from sots.classify.embedded import spawn_children
from sots.classify.review_queue import needs_review, relabel
from sots.classify.stats import document_stats
from sots.config import load_settings
from sots.models.document import Document
from sots.models.enums import Checkability, ContentType
from sots.models.unit import Unit
from sots.providers.fake import FakeProvider
from sots.providers.router import RoutingConfig, RoutingTask
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"


def _unit(uid: str, order: int, text: str, **fields: object) -> Unit:
    base: dict[str, object] = {
        "id": uid, "document_id": "d", "chunk_id": "c", "run_id": "r",
        "order": order, "text": text, "start_char": 0, "end_char": len(text),
    }
    base.update(fields)
    return Unit.model_validate(base)


def _routing() -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={
            name: RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=1000
            )
            for name in ("classify.safety_scan", "classify.unit")
        },
    )


def _out(content: str, confidence: float = 0.9, **fields: object) -> dict[str, object]:
    base: dict[str, object] = {
        "content_type": content, "claim_kind": None, "media_kind": None,
        "checkability": "not_checkable", "entities": [],
        "normalized_claim": None, "embedded_claims": [], "confidence": confidence,
    }
    base.update(fields)
    return base


async def test_stage_classifies_spawns_and_fails(tmp_path: Path) -> None:
    """T06.005/007: belief + factual-with-child + author-skip + FAILED."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        units = [
            _unit("u1", 0, "I believe grace precedes effort."),
            _unit("u2", 1, "I remember studies show rest heals."),
            _unit("u3", 2, "Author-owned words.", labeled_by="author",
                  content_type=ContentType.NARRATIVE_DEVICE,
                  checkability=Checkability.NOT_CHECKABLE,
                  classify_confidence=1.0),
            _unit("u4", 3, "Stubbornly weird words here."),
        ]
        for unit in units:
            storage_repo.save_unit(conn, unit)
        fake = FakeProvider()
        fake.script_default("classify.safety_scan", [{"text": '{"flags": []}'}])
        fake.script_default("classify.unit", [
            {"text": json.dumps(_out("personal_belief"))},
            {"text": json.dumps(_out(
                "personal_experience", checkability="partial",
                embedded_claims=["Studies show rest heals."],
            ))},
            {"text": json.dumps(_out(
                "factual_claim", claim_kind="academic_finding",
                checkability="checkable", normalized_claim="Rest heals.",
                entities=["rest"], embedded_claims=["nested claim"],
            ))},
            {"text": json.dumps(_out("personal_belief", claim_kind="statistic"))},
            {"text": json.dumps(_out("personal_belief", claim_kind="statistic"))},
        ])
        report = await run_classify_stage(
            "d", run_id="r", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
            batch_size=1, max_concurrency=1,
        )
        assert report.classified == ["u1", "u2"]
        assert report.failed == ["u4"]
        assert report.skipped_author == ["u3"]
        assert len(report.children) == 1
        assert report.flagged == []

        u1 = storage_repo.get_unit(conn, "u1")
        assert u1 is not None and u1.content_type == ContentType.PERSONAL_BELIEF
        assert u1.classify_confidence == 0.9 and u1.labeled_by == "model"

        child = storage_repo.get_unit(conn, report.children[0])
        assert child is not None
        assert child.parent_unit_id == "u2"
        assert (child.start_char, child.end_char) == (0, len(units[1].text))
        assert child.content_type == ContentType.FACTUAL_CLAIM
        assert child.text == "Studies show rest heals."

        u3 = storage_repo.get_unit(conn, "u3")
        assert u3 is not None and u3.content_type == ContentType.NARRATIVE_DEVICE
        assert u3.labeled_by == "author"

        u4 = storage_repo.get_unit(conn, "u4")
        assert u4 is not None and u4.content_type is None  # FAILED stays null
        events = storage_repo.list_events(conn, run_id="r")
        assert any(e["type"] == "classify.failed" for e in events)

        assert len(storage_repo.list_units(conn, document_id="d")) == 5  # no depth-2
        for uid in ("u1", "u2", "u4", report.children[0]):
            assert storage_repo.get_checkpoint(conn, uid) is not None
    finally:
        conn.close()


async def test_stage_resume_and_author_rerun(tmp_path: Path) -> None:
    """T06.007: checkpoints skip units; author labels survive re-runs."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        units = [
            _unit("u1", 0, "MARKERDONE first words here."),
            _unit("u2", 1, "MARKERTODO second words here."),
        ]
        for unit in units:
            storage_repo.save_unit(conn, unit)
        storage_repo.save_checkpoint(conn, "u1", {"status": "classified"}, run_id="r0")
        fake = FakeProvider()
        fake.script_default("classify.safety_scan", [{"text": '{"flags": []}'}])
        fake.script_default("classify.unit", [
            {"text": json.dumps(_out("personal_belief"))},
        ])
        kwargs = dict(
            run_id="r", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
            batch_size=1, max_concurrency=1,
        )
        report = await run_classify_stage("d", **kwargs)
        assert report.classified == ["u1", "u2"]
        bodies = [
            c.messages[0]["content"] for c in fake.calls if c.task == "classify.unit"
        ]
        assert bodies and all("MARKERDONE" not in b for b in bodies)

        relabel(conn, "u2", {"content_type": "narrative_device"})
        calls_before = len(fake.calls)
        rerun = await run_classify_stage("d", **kwargs)
        assert rerun.skipped_author == ["u2"]
        # Safety cache-hits; classify skips everything: zero new provider calls.
        assert len(fake.calls) == calls_before
        u2 = storage_repo.get_unit(conn, "u2")
        assert u2 is not None and u2.content_type == ContentType.NARRATIVE_DEVICE
        assert u2.labeled_by == "author"
    finally:
        conn.close()


def test_spawn_children_shape() -> None:
    """T06.005: same span, inherited entities, parent link, blanks skipped."""
    parent = _unit("p", 4, "Parent text here.", entities=["mom"])
    children = spawn_children(parent, ["  ", "Embedded fact one."], run_id="r")
    assert len(children) == 1
    child = children[0]
    assert child.parent_unit_id == "p"
    assert (child.start_char, child.end_char) == (parent.start_char, parent.end_char)
    assert child.entities == ["mom"]
    assert child.order == 4 and child.text == "Embedded fact one."
    assert child.content_type is None


def test_review_queue_query_and_relabel(tmp_path: Path) -> None:
    """T06.006: threshold query; relabel validates, coerces, marks author."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        for uid, conf, by in (
            ("u-high", 0.9, "model"), ("u-low", 0.5, "model"),
            ("u-none", None, "model"), ("u-author", 0.1, "author"),
        ):
            storage_repo.save_unit(conn, _unit(
                uid, 0, "T.", classify_confidence=conf, labeled_by=by,
            ))
        queued = needs_review(conn, threshold=0.6)
        assert sorted(u.id for u in queued) == ["u-low", "u-none"]
        queued_run = needs_review(conn, run_id="r", threshold=0.6)
        assert sorted(u.id for u in queued_run) == ["u-low", "u-none"]

        updated = relabel(conn, "u-low", {
            "content_type": "factual_claim", "claim_kind": "statistic",
            "checkability": "checkable", "classify_confidence": 1.0,
        })
        assert updated.content_type == ContentType.FACTUAL_CLAIM
        assert updated.labeled_by == "author"
        assert [u.id for u in needs_review(conn, threshold=0.6)] == ["u-none"]

        with pytest.raises(ValueError, match="cannot relabel"):
            relabel(conn, "u-low", {"text": "nope"})
        with pytest.raises(KeyError):
            relabel(conn, "u-missing", {"content_type": "narrative_device"})
    finally:
        conn.close()


def test_document_stats(tmp_path: Path) -> None:
    """T06.009: counts reconcile, unclassified slots read 'none'."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        storage_repo.save_unit(conn, _unit(
            "u1", 0, "A.", content_type=ContentType.PERSONAL_BELIEF,
            checkability=Checkability.NOT_CHECKABLE,
        ))
        storage_repo.save_unit(conn, _unit(
            "u2", 1, "B.", content_type=ContentType.FACTUAL_CLAIM,
            claim_kind="statistic", checkability=Checkability.CHECKABLE,
        ))
        storage_repo.save_unit(conn, _unit("u3", 2, "C."))
        stats = document_stats(conn, "d")
        assert stats.model_dump() == {
            "document_id": "d", "total": 3,
            "by_content_type": {
                "personal_belief": 1, "factual_claim": 1, "none": 1,
            },
            "by_claim_kind": {"none": 2, "statistic": 1},
            "by_checkability": {"not_checkable": 1, "checkable": 1, "none": 1},
        }
    finally:
        conn.close()


def test_child_spans_in_integrity(tmp_path: Path) -> None:
    """Children check against the parent span, not the canonical slice."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    text = "Parent words live here."
    (inbox / "doc1.txt").write_text(text, encoding="utf-8")
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        storage_repo.save_document(conn, Document(
            id="doc1", source_path="s", inbox_path=str(inbox / "raw.md"),
            sha256="0" * 64, title="T", chapter_id=None,
            char_count=len(text), word_count=4, ingested_at=datetime.now(UTC),
        ))
        parent = _unit("p1", 0, text)
        parent.document_id = "doc1"
        storage_repo.save_unit(conn, parent)
        good = _unit("c-good", 0, "Entirely different claim words.")
        good.document_id = "doc1"
        good.parent_unit_id = "p1"
        good.start_char = 0
        good.end_char = len(text)  # points at the parent span (05 §3.3)
        storage_repo.save_unit(conn, good)
        bad = _unit("c-bad", 0, "Escaped the span.")
        bad.document_id = "doc1"
        bad.parent_unit_id = "p1"
        bad.start_char = 0
        bad.end_char = len(text) + 50
        storage_repo.save_unit(conn, bad)
        orphan = _unit("c-orphan", 0, "No parent anywhere.")
        orphan.document_id = "doc1"
        orphan.parent_unit_id = "p-missing"
        storage_repo.save_unit(conn, orphan)
        report = check_all(InvariantContext(root=tmp_path, conn=conn))
        violations = report["offset_integrity"]
        assert any("c-bad" in v and "outside parent" in v for v in violations)
        assert any("c-orphan" in v and "missing" in v for v in violations)
        assert not any("c-good" in v for v in violations)
        assert not any(v.startswith("p1:") for v in violations)
    finally:
        conn.close()
