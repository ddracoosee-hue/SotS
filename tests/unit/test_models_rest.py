"""P01 slice D (T01.018-T01.020): audience/legal/learning round-trips."""

from __future__ import annotations

from datetime import datetime

import pytest

from sots.errors import AdultsOnlyViolation
from sots.models.audience import (
    AudienceBrief,
    AudienceScorecard,
    BriefItem,
    CalibrationRecord,
    MechanicsFinding,
    Persona,
    PersonaReaction,
    PlaybookEntry,
    QuoteRef,
)
from sots.models.enums import Severity
from sots.models.learning import LearningChange, PromptTrial
from sots.models.legal import Authority, DefenseMemo, LegalIssue, Position


def _round_trip(model: object) -> None:
    cls = type(model)
    assert cls.model_validate(model.model_dump()) == model
    assert cls.model_validate_json(model.model_dump_json()) == model


def _sample_persona(**overrides: object) -> Persona:
    fields: dict[str, object] = {
        "id": "p01",
        "name": "Persona 01",
        "cohort": "gen_z_adult",
        "age": 22,
        "life_stage": "final year of university",
        "region": "mid-size US city",
        "background_notes": "individual notes",
        "reading_habits": "reads nonfiction on the commute",
        "need_for_cognition": "high",
        "current_season": "anxious about the job market",
        "skepticism": "distrusts influencer advice",
        "values": ["authenticity", "fairness"],
        "what_would_make_them_close_the_book": "being lectured",
    }
    fields.update(overrides)
    return Persona(**fields)  # type: ignore[arg-type]


def _sample_quote() -> QuoteRef:
    return QuoteRef(unit_id="unit_1", quote="a line worth keeping", note="resonant")


def test_persona_round_trip() -> None:
    _round_trip(_sample_persona())


def test_persona_age_17_raises() -> None:
    with pytest.raises(AdultsOnlyViolation):
        _sample_persona(age=17)


def test_persona_age_18_passes() -> None:
    assert _sample_persona(age=18).age == 18


def test_quote_ref_round_trip() -> None:
    _round_trip(_sample_quote())


def test_mechanics_finding_round_trip() -> None:
    _round_trip(
        MechanicsFinding(
            id="mf_1",
            analyst="tonality",
            revision_id="rev_1",
            unit_ids=["unit_1"],
            metric="controlling-language index",
            value=5.0,
            threshold=4.0,
            issue="preachy stretch",
            suggestion="offer options instead of orders",
            severity=Severity.MEDIUM,
        )
    )


def test_persona_reaction_round_trip() -> None:
    _round_trip(
        PersonaReaction(
            id="pr_1",
            persona_id="p01",
            sample=1,
            revision_id="rev_1",
            section_id="sec_1",
            first_impression="honest and direct",
            felt=["seen", "curious"],
            recognition=8.0,
            felt_judged=2.0,
            curiosity=7.0,
            absorption=7.5,
            insight=6.0,
            agency=7.0,
            preachiness=2.0,
            credibility=8.0,
            intellectual_respect=8.5,
            relatability=7.0,
            would_continue=8.0,
            would_share=6.0,
            confusing_parts=[_sample_quote()],
            cringe_parts=[],
            strongest_line=_sample_quote(),
            takeaway_in_own_words="start with the story, not the lesson",
            disagreements=[],
            question_for_author=None,
        )
    )


def test_audience_scorecard_round_trip() -> None:
    _round_trip(
        AudienceScorecard(
            id="sc_1",
            revision_id="rev_1",
            metric_means={"credibility": 7.6},
            cohort_means={"gen_z_adult": {"credibility": 7.8}},
            metric_sd={"credibility": 1.1},
            metric_min={"credibility": 5.0},
            metric_max={"credibility": 9.5},
            message_reception_rate=0.82,
            journey_curve={"J1": [8.0, 7.5]},
            hotspots=["unit_3"],
            strong_lines=["unit_1"],
        )
    )


def test_brief_item_round_trip() -> None:
    _round_trip(
        BriefItem(
            unit_ids=["unit_3"],
            problem="preachy stretch",
            evidence="pr_1,pr_2 preachiness 6.5",
            direction="reframe as options",
            protect=["unit_1"],
        )
    )


def test_audience_brief_round_trip() -> None:
    _round_trip(
        AudienceBrief(
            id="ab_1",
            revision_id="rev_1",
            scorecard_id="sc_1",
            priorities=[
                BriefItem(
                    unit_ids=["unit_3"],
                    problem="preachy stretch",
                    evidence="pr_1 preachiness 6.5",
                    direction="reframe as options",
                    protect=["unit_1"],
                )
            ],
            do_not_touch=["unit_1"],
            voice_cautions=["keep the dry humor"],
        )
    )


def test_calibration_record_round_trip() -> None:
    _round_trip(
        CalibrationRecord(
            id="cal_1",
            metric="credibility",
            cohort="gen_z_adult",
            synthetic_mean=7.6,
            real_mean=7.1,
            bias=0.5,
            correlation=0.62,
            real_respondents=8,
            unreliable=False,
        )
    )


def test_playbook_entry_round_trip() -> None:
    _round_trip(
        PlaybookEntry(
            technique="story_before_lesson",
            cohort="gen_z_adult",
            metric="absorption",
            alpha=9.0,
            beta=3.0,
            trials=12,
        )
    )


def test_legal_issue_round_trip() -> None:
    _round_trip(
        LegalIssue(
            id="li_1",
            run_id="run_1",
            revision_id="rev_1",
            unit_ids=["unit_9"],
            issue_types=["defamation", "ethics"],
            persons_involved=[{"name_or_descriptor": "a creator", "identifiable": True}],
            preliminary_risk=Severity.HIGH,
            assigned_counsel=["L1", "L4", "L8"],
            status="open",
        )
    )


def test_authority_round_trip() -> None:
    _round_trip(
        Authority(
            kind="case",
            citation="Example v. Example, 123 F.4th 1 (2020)",
            jurisdiction="US",
            evidence_id="ev_1",
        )
    )


def test_position_round_trip() -> None:
    _round_trip(
        Position(
            id="pos_1",
            issue_id="li_1",
            counsel="L1",
            round=2,
            stance="safe_with_edits",
            risk=Severity.MEDIUM,
            argument="frame the evaluation as opinion",
            authorities=[
                Authority(
                    kind="case",
                    citation="Example v. Example",
                    jurisdiction="US",
                    evidence_id="ev_1",
                )
            ],
            proposed_edits=[{"unit_id": "unit_9", "direction": "reframe as opinion"}],
            rebuttals=[{"position_id": "pos_2", "rebut": True, "reason": "cites no source"}],
            argument_score=88.5,
        )
    )


def test_defense_memo_round_trip() -> None:
    _round_trip(
        DefenseMemo(
            id="dm_1",
            issue_id="li_1",
            text_position="the text claims the creator did X",
            defense_basis=["opinion", "truth_substantial_truth"],
            argument="the claim is verified and framed as opinion",
            required_edits=[{"unit_id": "unit_9", "direction": "add attribution"}],
            residual_risk=Severity.LOW,
            answered_dissents=[{"position_id": "pos_2", "answer": "outweighed by evidence"}],
            endorsements={"L1": "endorse", "L4": "endorse_with_reservations"},
            grade_id="gr_1",
            needs_licensed_attorney=False,
        )
    )


def test_learning_change_round_trip() -> None:
    _round_trip(
        LearningChange(
            id="lc_1",
            kind="threshold",
            target="audience.targets.primary_cohort.mrr",
            before="0.80",
            after="0.75",
            evidence="calibration cal_1: bias +0.5 over 3 chapters",
            status="applied",
            applied_at=datetime(2026, 9, 28, 12, 0, 0),
        )
    )


def test_prompt_trial_round_trip() -> None:
    _round_trip(
        PromptTrial(
            id="pt_1",
            prompt_id="audience.brief",
            baseline_version=1,
            candidate_version=2,
            metric_deltas={"grade": 1.5},
            release_blocker_regressions=[],
            promoted=True,
        )
    )
