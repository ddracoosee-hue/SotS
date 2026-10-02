"""P01 slice A (T01.001-T01.006): ids, enums, document/unit/evidence/verdict models."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from sots.models.document import Chunk, Document
from sots.models.enums import (
    Checkability,
    ClaimKind,
    ContentType,
    MediaKind,
    SourceClass,
    StageStatus,
    Stance,
    Verdict,
)
from sots.models.evidence import Evidence, FetchedDoc, SearchHit
from sots.models.ids import new_id
from sots.models.unit import Unit
from sots.models.verdict import DiscoveryNote, RuleCheck, SpecialistFindings, VerdictRecord


def test_new_id_keeps_prefix() -> None:
    assert new_id("unit").startswith("unit_")
    assert new_id("doc").startswith("doc_")


def test_new_id_unique_and_time_sortable() -> None:
    ids = [new_id("unit") for _ in range(10_000)]
    assert len(set(ids)) == 10_000
    assert ids == sorted(ids)


def test_verdict_strength_order() -> None:
    expected = [
        Verdict.TRUE,
        Verdict.MOSTLY_TRUE,
        Verdict.PARTIALLY_TRUE,
        Verdict.MISLEADING,
        Verdict.FALSE,
        Verdict.UNSUPPORTED,
        Verdict.UNVERIFIABLE,
        Verdict.NOT_CHECKABLE,
        Verdict.FAILED,
    ]
    assert [v.strength() for v in expected] == list(range(len(expected)))
    assert list(Verdict) == expected


def test_document_round_trip() -> None:
    doc = Document(
        id=new_id("doc"),
        source_path="draft/ch01.md",
        inbox_path="data/inbox/abc.md",
        sha256="0" * 64,
        title="Chapter 1",
        chapter_id="ch01",
        char_count=100,
        word_count=20,
        ingested_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    assert Document.model_validate(doc.model_dump()) == doc


def test_chunk_round_trip() -> None:
    chunk = Chunk(
        id=new_id("chk"),
        document_id=new_id("doc"),
        index=0,
        start_char=0,
        end_char=500,
        token_estimate=120,
    )
    assert Chunk.model_validate(chunk.model_dump()) == chunk


def test_unit_round_trip_and_mutable() -> None:
    unit = Unit(
        id=new_id("unit"),
        document_id=new_id("doc"),
        chunk_id=new_id("chk"),
        run_id=new_id("run"),
        order=3,
        text="The author wrote this sentence.",
        start_char=10,
        end_char=41,
        content_type=ContentType.FACTUAL_CLAIM,
        claim_kind=ClaimKind.STATISTIC,
        media_kind=None,
        checkability=Checkability.CHECKABLE,
        entities=["World Bank"],
        normalized_claim="A neutral restatement.",
        classify_confidence=0.9,
        safety_flag=False,
        parent_unit_id=None,
        block=2,
        prompt_id="ch03.B2.P1",
        anchor_ids=["anchor_1"],
        labeled_by="model",
        revision_offsets={"rev_1": (10, 41)},
    )
    assert Unit.model_validate(unit.model_dump()) == unit
    unit.text = "edited"
    assert unit.text == "edited"
    assert Unit.model_validate(unit.model_dump(mode="json")) == unit


def test_unit_defaults() -> None:
    unit = Unit(
        id="unit_x",
        document_id="doc_x",
        chunk_id="chk_x",
        run_id="run_x",
        order=0,
        text="t",
        start_char=0,
        end_char=1,
    )
    assert unit.labeled_by == "model"
    assert unit.revision_offsets == {}
    assert unit.entities == []


def test_evidence_round_trip() -> None:
    ev = Evidence(
        id=new_id("ev"),
        unit_id=new_id("unit"),
        url="https://example.gov/data",
        title="Official data",
        publisher="Example",
        published_date=date(2025, 6, 1),
        accessed_at=datetime(2026, 1, 2, 8, 0, 0),
        source_class=SourceClass.PRIMARY_RECORD,
        tier=1,
        excerpt="verbatim text",
        excerpt_match_score=100.0,
        stance=Stance.SUPPORTS,
        fetcher="web",
        content_hash="abc123",
    )
    assert Evidence.model_validate(ev.model_dump()) == ev
    assert Evidence.model_validate(ev.model_dump(mode="json")) == ev


def test_fetched_doc_round_trip() -> None:
    doc = FetchedDoc(
        url="https://example.com/page",
        title="A page",
        publisher=None,
        published_date=None,
        text="readable text",
        content_hash="hash1",
        fetcher="web",
    )
    assert FetchedDoc.model_validate(doc.model_dump()) == doc


def test_search_hit_round_trip() -> None:
    hit = SearchHit(url="https://example.com", title="T", snippet="snip", rank=1)
    assert SearchHit.model_validate(hit.model_dump()) == hit


def test_rule_check_round_trip() -> None:
    check = RuleCheck(rule_id="VR-STAT-01", passed=False, cap=Verdict.PARTIALLY_TRUE, note="x")
    assert RuleCheck.model_validate(check.model_dump()) == check


def test_verdict_record_round_trip() -> None:
    record = VerdictRecord(
        id=new_id("vd"),
        unit_id=new_id("unit"),
        run_id=new_id("run"),
        proposed_verdict=Verdict.TRUE,
        final_verdict=Verdict.MOSTLY_TRUE,
        truth_basis=SourceClass.ACADEMIC,
        confidence=0.75,
        evidence_ids=[new_id("ev")],
        researcher_summary="summary",
        skeptic_objections=["objection"],
        adjudicator_reasoning="reasoning",
        rule_checks=[RuleCheck(rule_id="VR-GEN-02", passed=True, cap=None, note="ok")],
        what_is_accurate="the year",
        what_is_off="the percentage",
        suggested_correction="neutral wording",
        claim_specific={"value_claimed": 42, "value_found": 40},
        epistemic_tier="PT",
        tier_claimed_by_author=None,
    )
    assert VerdictRecord.model_validate(record.model_dump()) == record
    assert VerdictRecord.model_validate(record.model_dump(mode="json")) == record


def test_specialist_findings_round_trip() -> None:
    findings = SpecialistFindings(
        unit_id=new_id("unit"),
        specialist="stats",
        evidence_ids=[new_id("ev")],
        claim_specific={"value_found": 40},
    )
    assert SpecialistFindings.model_validate(findings.model_dump()) == findings


def test_discovery_note_round_trip() -> None:
    note = DiscoveryNote(
        id=new_id("disc"),
        unit_id=new_id("unit"),
        agent="stats",
        kind="newer_data",
        summary="A newer figure exists.",
        evidence_id=new_id("ev"),
        why_interesting="More current than the author's figure.",
    )
    assert DiscoveryNote.model_validate(note.model_dump()) == note


def test_models_frozen_except_unit() -> None:
    doc = Document(
        id="d",
        source_path="s",
        inbox_path="i",
        sha256="h",
        title="t",
        chapter_id=None,
        char_count=1,
        word_count=1,
        ingested_at=datetime(2026, 1, 1),
    )
    with pytest.raises(ValidationError):
        doc.title = "other"  # type: ignore[misc]
    hit = SearchHit(url="u", title="t", snippet="s", rank=0)
    with pytest.raises(ValidationError):
        hit.rank = 2  # type: ignore[misc]


def test_extra_forbidden() -> None:
    with pytest.raises(ValidationError):
        SearchHit(url="u", title="t", snippet="s", rank=0, bogus=1)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="not_a_kind"):
        MediaKind("not_a_kind")
    assert StageStatus.DONE.value == "done"
