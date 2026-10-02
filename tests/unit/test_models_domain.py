"""P01 slice B (T01.007-T01.012): domain model round-trips."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from sots.models.enums import MediaKind, Severity, StageStatus
from sots.models.media import MediaCheck, MediaPoint, MediaWork
from sots.models.narrative import (
    CoreMessage,
    DriftReport,
    MessageMapping,
    VoiceComparison,
    VoiceFingerprint,
)
from sots.models.profile import AuthorProfile, BookProfile, ChapterBrief
from sots.models.psyche import EngineFinding, Synthesis
from sots.models.run import ChapterState, LLMCall, Run
from sots.models.shadow import RubricScore, ShadowItem, ShadowReport


def _round_trip(model: object) -> None:
    cls = type(model)
    assert cls.model_validate(model.model_dump()) == model
    assert cls.model_validate_json(model.model_dump_json()) == model


def _sample_work() -> MediaWork:
    return MediaWork(
        id="work_01J9X",
        kind=MediaKind.FILM,
        title="Sample Film",
        creators=["Jane Director"],
        year=1999,
        external_ids={"tmdb": "123"},
        resolved=True,
    )


def test_media_work_round_trip() -> None:
    _round_trip(_sample_work())


def test_media_point_round_trip() -> None:
    _round_trip(
        MediaPoint(
            statement="The film ends with a duel.",
            point_type="plot_fact",
            accuracy="accurate",
            correction=None,
            evidence_ids=["ev_1"],
        )
    )


def test_media_check_round_trip() -> None:
    _round_trip(
        MediaCheck(
            id="mc_1",
            unit_id="unit_1",
            run_id="run_1",
            work=_sample_work(),
            points=[
                MediaPoint(
                    statement="A quote.",
                    point_type="quote",
                    accuracy="partly_accurate",
                    correction="Actual wording.",
                    evidence_ids=[],
                )
            ],
            author_reading="It means hope.",
            established_readings=["Critics read it as hope."],
            interpretation_status="supported_reading",
            message_alignment=0.8,
            use_in_book_note="Serves the point well.",
        )
    )


def test_engine_finding_round_trip() -> None:
    _round_trip(
        EngineFinding(
            id="pf_1",
            run_id="run_1",
            engine="blindspot",
            finding_type="avoidance",
            unit_ids=["unit_1"],
            summary="Avoids the topic.",
            detail="Longer detail.",
            confidence=0.7,
            severity=Severity.MEDIUM,
            responds_to=["pf_0"],
            question_for_author="Why skip this?",
        )
    )


def test_engine_finding_defaults() -> None:
    finding = EngineFinding(
        id="pf_2",
        run_id="run_1",
        engine="emotion",
        finding_type="grief",
        unit_ids=["unit_2"],
        summary="Grief present.",
        detail="Detail.",
        confidence=0.9,
        severity=Severity.LOW,
        question_for_author=None,
    )
    assert finding.responds_to == []
    _round_trip(finding)


def test_synthesis_round_trip() -> None:
    _round_trip(
        Synthesis(
            run_id="run_1",
            agreements=["Both see grief."],
            tensions=["Theme vs emotion."],
            top_insights=["Insight citing pf_1."],
            finding_ids=["pf_1", "pf_2"],
        )
    )


def test_core_message_round_trip() -> None:
    _round_trip(
        CoreMessage(
            id="M1",
            level="book",
            chapter_id=None,
            statement="Know thyself.",
            priority=1,
        )
    )


def test_message_mapping_round_trip() -> None:
    _round_trip(
        MessageMapping(unit_id="unit_1", message_id="M1", role="illustrates", strength=0.6)
    )


def test_drift_report_round_trip() -> None:
    _round_trip(
        DriftReport(
            run_id="run_1",
            document_id="doc_1",
            coverage={"M1": 0.7},
            unmapped_ratio=0.3,
            drift_segments=[(3, 7)],
            missing_messages=["M2"],
            flow_breaks=["unit_5"],
        )
    )


def test_voice_fingerprint_round_trip() -> None:
    _round_trip(
        VoiceFingerprint(
            source="voice_corpus",
            avg_sentence_len=14.5,
            sentence_len_stdev=5.2,
            type_token_ratio=0.42,
            punctuation_profile={"comma": 12.0},
            person_ratio={"first": 0.6, "second": 0.1, "third": 0.3},
            signature_phrases=["here is the thing"],
            llm_style_description="Plain and direct.",
        )
    )


def test_voice_comparison_round_trip() -> None:
    _round_trip(
        VoiceComparison(
            run_id="run_1",
            document_id="doc_1",
            similarity=0.82,
            deviations=["Longer sentences."],
            off_voice_unit_ids=["unit_9"],
        )
    )


def test_shadow_item_round_trip() -> None:
    _round_trip(
        ShadowItem(
            category="contradiction",
            unit_ids=["unit_1", "unit_4"],
            observation="Says both X and not-X.",
            question_for_author="Which is it?",
            severity=Severity.HIGH,
        )
    )


def test_rubric_score_round_trip() -> None:
    _round_trip(
        RubricScore(
            criterion_id="clarity",
            score=4,
            measured_value=0.8,
            target=0.9,
            met=False,
            justification="Close but under target.",
            unit_ids=["unit_1"],
        )
    )


def test_shadow_report_round_trip() -> None:
    _round_trip(
        ShadowReport(
            id="sh_1",
            run_id="run_1",
            document_id="doc_1",
            items=[
                ShadowItem(
                    category="avoidance",
                    unit_ids=["unit_2"],
                    observation="Skirts the issue.",
                    question_for_author="What is missing?",
                    severity=Severity.LOW,
                )
            ],
            scores=[
                RubricScore(
                    criterion_id="clarity",
                    score=3,
                    measured_value=None,
                    target=None,
                    met=True,
                    justification="Fine.",
                    unit_ids=[],
                )
            ],
            overall=3.0,
            goals_met=1,
            goals_total=2,
            trend_vs_previous={"clarity": 0.5},
        )
    )


def test_author_profile_round_trip() -> None:
    _round_trip(
        AuthorProfile(
            name_or_pen_name="J. Doe",
            background="Teacher.",
            why_this_book="To help.",
            lived_experience_areas=["teaching"],
            sensitive_topics=["grief"],
            values=["honesty"],
            known_biases_self_reported=["optimism"],
        )
    )


def test_book_profile_round_trip() -> None:
    _round_trip(
        BookProfile(
            working_title="Working Title",
            genre="self_help_reflective",
            premise="Know yourself.",
            target_reader="Seekers.",
            promise_to_reader="Clarity.",
            tone_goals=["warm"],
            out_of_scope=["politics"],
            media_exclusions=["horror"],
        )
    )


def test_chapter_brief_round_trip() -> None:
    _round_trip(
        ChapterBrief(
            chapter_id="ch01",
            title="Begin",
            purpose="Open the book.",
            key_messages=["Start well."],
            planned_stories=["A childhood story."],
            planned_references=["A study."],
            reader_takeaway="Hope.",
            raw_brief="Original brief text.",
            reader_journey="From doubt to hope.",
        )
    )


def test_chapter_brief_reader_journey_optional() -> None:
    brief = ChapterBrief(
        chapter_id="ch02",
        title="Next",
        purpose="Continue.",
        key_messages=[],
        planned_stories=[],
        planned_references=[],
        reader_takeaway="More.",
        raw_brief="Raw.",
    )
    assert brief.reader_journey is None


def test_run_round_trip_and_mutable() -> None:
    run = Run(
        id="run_1",
        document_ids=["doc_1"],
        started_at=datetime(2026, 9, 29, 6, 0, 0),
        finished_at=None,
        stage_status={"ingest": StageStatus.DONE},
        budget_tokens=1000,
        used_tokens=10,
        cost_estimate=0.01,
        config_snapshot={"k": "v"},
    )
    run.used_tokens = 20  # mutable
    assert run.used_tokens == 20
    _round_trip(run)


def test_llm_call_round_trip() -> None:
    _round_trip(
        LLMCall(
            id="llm_1",
            run_id="run_1",
            task="verify.skeptic",
            provider="test",
            model="test-model",
            prompt_id="skeptic",
            prompt_version=1,
            input_hash="abc",
            input_tokens=100,
            output_tokens=50,
            cost_estimate=0.001,
            latency_ms=200,
            status="ok",
            created_at=datetime(2026, 9, 29, 6, 0, 0),
        )
    )


def test_chapter_state_round_trip() -> None:
    _round_trip(
        ChapterState(
            chapter_id="ch01",
            act=1,
            gate_status={"truth": "passed"},
            blocked_reasons=[],
        )
    )


def test_frozen_models_reject_mutation() -> None:
    brief = ChapterBrief(
        chapter_id="ch01",
        title="T",
        purpose="P",
        key_messages=[],
        planned_stories=[],
        planned_references=[],
        reader_takeaway="R",
        raw_brief="B",
    )
    with pytest.raises(ValidationError):
        brief.title = "other"  # type: ignore[misc]
