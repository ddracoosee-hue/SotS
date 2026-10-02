"""P04A coverage + book-integrity tests (T04A.033, T04A.040-042, 23 §5/§7)."""

from __future__ import annotations

from pathlib import Path

from sots.foundation.architecture import Architecture
from sots.foundation.loader import load_foundation
from sots.foundation.protocol_load import ProtocolLoadInput, audit_protocol_load
from sots.models.foundation import Block, ChapterBrief
from sots.models.unit import Unit
from sots.narrative.repetition import TreatmentClaim, check_repetition
from sots.reports.sections.dictation_coverage import chapter_coverage
from sots.shadow.arc_consistency import check_arc

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "profile"


def _brief_texts() -> dict[str, str]:
    chapters = PROFILE_DIR / "chapters"
    return {
        f"ch{i:02d}": (chapters / f"ch{i:02d}_brief.md").read_text(encoding="utf-8")
        for i in range(1, 13)
    }


def _brief() -> ChapterBrief:
    return ChapterBrief(
        chapter_id="ch03", title="T", subtitle="S", core_theme="C",
        blocks=[
            Block.model_validate({
                "number": 1, "name": "hook_targeting", "structural_purpose": "Hook.",
                "anchors": ["ch03.A01", "ch01.A05"],
                "dictation_prompts": [
                    {"id": "ch03.B1.P1", "text": "P1."},
                    {"id": "ch03.B1.P2", "text": "P2."},
                ],
            }),
            Block.model_validate({
                "number": 2, "name": "paradigm_shift", "structural_purpose": "Flip.",
                "old_belief": "o", "new_belief": "n", "anchors": ["ch03.A09"],
                "dictation_prompts": [{"id": "ch03.B2.P1", "text": "P3."}],
            }),
        ],
    )


def _unit(uid: str, order: int, prompt_id: str | None, anchors: list[str]) -> Unit:
    return Unit(
        id=uid, document_id="d", chunk_id="c", run_id="r", order=order,
        text="t", start_char=0, end_char=1,
        prompt_id=prompt_id, anchor_ids=anchors,
    )


def test_coverage_snapshot() -> None:
    """T04A.033: full ChapterCoverage frozen as a literal."""
    coverage = chapter_coverage(_brief(), [
        _unit("u1", 0, "ch03.B1.P1", ["ch03.A01"]),
        _unit("u2", 1, "ch03.B1.P1", []),
        _unit("u3", 2, None, ["ch03.A09"]),
    ])
    assert coverage.model_dump() == {
        "chapter_id": "ch03",
        "prompts": [
            {"prompt_id": "ch03.B1.P1", "status": "answered", "unit_ids": ["u1", "u2"]},
            {"prompt_id": "ch03.B1.P2", "status": "partial", "unit_ids": []},
            {"prompt_id": "ch03.B2.P1", "status": "missing", "unit_ids": []},
        ],
        "anchors_used": ["ch03.A01", "ch03.A09"],
        "anchors_planned": ["ch01.A05", "ch03.A01", "ch03.A09"],
        "anchors_unused": ["ch01.A05"],
    }


def _architecture() -> Architecture:
    return Architecture(load_foundation(PROFILE_DIR).architecture)


def test_protocol_load_reading_order_36() -> None:
    """T04A.040/23 §7: 36 protocols, 3 per chapter, cumulatives in order."""
    arch = _architecture()
    protocols = [
        ProtocolLoadInput(id=f"{ch}.P{i}", chapter=ch, minutes_per_week=10 * i)
        for ch in arch.reading_order
        for i in (1, 2, 3)
    ]
    report = audit_protocol_load(protocols, arch)
    assert report.total_min_per_week == 12 * 60
    assert report.active_count == 36
    assert report.over_budget is True
    assert [c.chapter for c in report.by_chapter] == arch.reading_order
    assert all(c.minutes == 60 for c in report.by_chapter)
    assert [c.cumulative_minutes for c in report.by_chapter] == [60 * (i + 1) for i in range(12)]
    assert len(report.findings) == 3
    assert "36 active protocols" in report.findings[0]
    assert "12.0 h/week" in report.findings[1]


def test_repetition_claims() -> None:
    """T04A.041/23 §7: full-where-callback-planned is flagged."""
    arch = _architecture()
    issues = check_repetition([
        TreatmentClaim(motif="Harvard Study", chapter="ch08", treatment="full"),
        TreatmentClaim(motif="Harvard Study", chapter="ch06", treatment="full"),
        TreatmentClaim(motif="Harvard Study", chapter="ch08", treatment="callback"),
        TreatmentClaim(motif="Unknown Motif", chapter="ch08", treatment="full"),
    ], arch)
    assert [(i.motif, i.chapter, i.expected, i.claimed) for i in issues] == [
        ("Harvard Study", "ch08", "callback", "full"),
    ]


def test_arc_full_snapshot() -> None:
    """T04A.042: every chapter's arc issues, frozen (23 §7).

    ch04/ch06/ch07 are the blueprint-known conflicts; ch11's Phase 4 label
    is confirmed by its required brief edit (-> 'Phase 3 climax').
    """
    arch = _architecture()
    texts = _brief_texts()
    kinds = {
        chapter: [i.kind for i in check_arc(chapter, texts[chapter], arch)]
        for chapter in arch.reading_order
    }
    assert kinds == {
        "ch01": [], "ch02": [], "ch03": [], "ch04": ["chapter_count"],
        "ch05": [], "ch07": ["capstone_claim"], "ch10": [],
        "ch11": ["phase_label"], "ch09": [], "ch06": ["capstone_claim"],
        "ch12": [], "ch08": [],
    }
    ch11 = check_arc("ch11", texts["ch11"], arch)
    assert ch11[0].expected == "architecture phase P3"
    # ch08's [] is a Keep approval, not an absence: the language is there.
    assert "capstone" in texts["ch08"].lower()


def test_arc_forward_references() -> None:
    """Backward language to later chapters (and reverse) is caught."""
    arch = _architecture()
    later = check_arc("ch04", "As we saw in Chapter 9, hope holds.", arch)
    assert [i.kind for i in later] == ["forward_ref"]
    earlier = check_arc("ch04", "We will see this later in Chapter 2.", arch)
    assert [i.kind for i in earlier] == ["forward_ref"]
    fine = check_arc("ch04", "As we saw in Chapter 2, hope holds.", arch)
    assert fine == []
