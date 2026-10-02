"""P01 slice C (T01.013-T01.017): expansion, agents, grading, proposal, rewrite."""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

import pytest
from pydantic import BaseModel, ValidationError

from sots.models import agents as m_agents
from sots.models import expansion as m_exp
from sots.models import grading as m_grade
from sots.models import proposal as m_prop
from sots.models import rewrite as m_rw

T = TypeVar("T")


def roundtrip(model: BaseModel) -> BaseModel:
    return type(model).model_validate(model.model_dump())


def test_expansion_roundtrips() -> None:
    concept = m_exp.Concept(
        id="con_1",
        label="people-pleasing as survival",
        definition="SYSTEM text.",
        unit_ids=["unit_1"],
        chapter_ids=["ch01"],
        message_ids=["M1"],
        maturity="seed",
    )
    assert roundtrip(concept) == concept
    edge = m_exp.ConceptEdge(
        source_id="con_1",
        target_id="con_2",
        relation="causes",
        rationale="r",
        unit_ids=[],
        inferred=True,
    )
    assert roundtrip(edge) == edge
    graph = m_exp.ConceptGraph(
        run_id="run_1", concepts=[concept], edges=[edge],
        hubs=["con_1"], bridges=[], orphans=[],
    )
    assert roundtrip(graph) == graph
    thread = m_exp.ExpansionThread(
        id="thr_1", title="t", kind="deepen", concept_ids=["con_1"],
        message_ids=["M1"], rationale="r", estimated_tokens=100,
        status="proposed", critic_score=None,
    )
    assert roundtrip(thread) == thread
    brief = m_exp.ResearchBrief(
        thread_id="thr_1", central_question="q", why_it_matters="w",
        author_starting_point=["unit_1"], sub_questions=["q1", "q2", "q3"],
        must_find=["study", "counter_view"], exclusions=[],
        max_depth=3, max_sources=25,
    )
    assert roundtrip(brief) == brief
    note = m_exp.ResearchNote(
        id="note_1", thread_id="thr_1", sub_question="q1", claim="c",
        evidence_id="ev_1", depth=1, novelty=0.9, leads=["l1"],
    )
    assert roundtrip(note) == note
    stmt = m_exp.ReportStatement(
        text="s", origin=m_exp.Origin.SYSTEM, note_ids=["note_1"], unit_ids=[],
    )
    assert roundtrip(stmt) == stmt
    section = m_exp.ReportSection(heading="h", statements=[stmt])
    assert roundtrip(section) == section
    report = m_exp.DeepResearchReport(
        id="rep_1", thread_id="thr_1", title="t", executive_summary=[stmt],
        sections=[section], counter_perspectives=section,
        connections_to_author_text=section, new_concepts=[],
        open_questions=["o"], source_mix={"academic": 2}, saturation_curve=[1.0, 0.2],
    )
    assert roundtrip(report) == report
    margin = m_exp.MarginNote(
        id="mn_1", unit_id="unit_1", kind="echo", text="t",
        origin=m_exp.Origin.SYSTEM, links=["unit_2"], status="open",
    )
    assert roundtrip(margin) == margin
    ib = m_exp.IntegrationBrief(
        id="ib_1", report_id="rep_1", chapter_id="ch01",
        placements=[{"after_unit_id": "unit_1"}], new_message_candidates=[],
        restructure_suggestions=[], questions_for_author=["q"], risks=["r"],
    )
    assert roundtrip(ib) == ib
    critic = m_exp.CriticScore(
        target_id="thr_1", relevance=0.8, grounding=1.0, novelty=0.7,
        voice_respect=0.9, balance=0.8, verdict="accept", reasons=["r"],
    )
    assert roundtrip(critic) == critic


def _card(**over: object) -> m_agents.AgentCard:
    base: dict[str, object] = {
        "name": "tester",
        "team": "fact_check",
        "role": "r",
        "prompts": {"system": "s.md", "step": "t.md"},
        "output_model": "sots.models.rewrite.CrossCheckReport",
        "routing_task": "rewrite.cross_check",
        "tools": ["web_search"],
        "internet": True,
        "limits": {"max_steps": 5, "max_tokens": 1000, "timeout_s": 60, "max_retries": 2},
        "grading": {"rubric": None},
        "failsafes": ["F01", "F02"],
        "on_failure": "dead_letter",
    }
    base.update(over)
    return m_agents.AgentCard.model_validate(base)


def test_agents_roundtrips() -> None:
    assert roundtrip(_card()) == _card()
    action = m_agents.AgentAction(
        type="tool", tool="web_search", args={"q": "x"}, thought="t", final=None,
    )
    assert roundtrip(action) == action
    obs = m_agents.Observation(tool="web_search", ok=True, content="c", truncated=False)
    assert roundtrip(obs) == obs
    now = datetime(2026, 1, 1, 12, 0, 0)
    run = m_agents.AgentRun(
        id="ar_1", run_id="run_1", agent="a", team="t", act="I",
        started_at=now, finished_at=None, steps=1, tokens_in=10, tokens_out=5,
        cost=0.01, status="ok", failure_code=None, grade_attempts=0,
        final_grade=None, checkpoint_key="k",
    )
    assert roundtrip(run) == run
    res = m_agents.AgentResult[str](agent="a", status="ok", output="done", error=None)
    assert m_agents.AgentResult[str].model_validate(res.model_dump()) == res
    sl = m_agents.BudgetSlice(
        scope="run_1/I/fact_check", tokens_allowed=1000, cost_allowed=1.0,
    )
    assert roundtrip(sl) == sl


def test_agent_card_rejects_unknown_failsafe_ids() -> None:
    with pytest.raises(ValidationError):
        _card(failsafes=["F01", "F99"])
    with pytest.raises(ValidationError):
        _card(failsafes=["bogus"])


def test_grading_roundtrips() -> None:
    crit = m_grade.CriterionResult(
        id="R1", type="measured", score=5.0, floor=4.0,
        evidence="e", judges={"judge_a": 5.0},
    )
    assert roundtrip(crit) == crit
    rec = m_grade.GradeRecord(
        id="gr_1", artifact_type="proposal", artifact_id="prop_1", attempt=1,
        rubric_id="proposal", rubric_version=1, criteria=[crit], score=97.0,
        passed=True, feedback_for_generator=[], created_at=datetime(2026, 1, 1),
    )
    assert roundtrip(rec) == rec
    health = m_grade.GraderHealth(
        window_grades=50, first_attempt_pass_rate=0.5, author_reject_rate=0.1,
        pass_within_max_rate=0.9, tiebreak_rate=0.1, too_lenient=False,
        too_strict=False, judge_disagreement=False, top_rejection_reasons=["off_message"],
    )
    assert roundtrip(health) == health


def _placement(pid: str) -> m_prop.PlacementOption:
    return m_prop.PlacementOption(
        id=pid, location="after_unit", anchor_unit_id="unit_1", chapter_id="ch01",
        rationale="r", preview_outline=["b1"],
    )


def _mode(mid: str) -> m_prop.IntegrationMode:
    return m_prop.IntegrationMode(
        id=mid, mode="brief_mention", description="d", word_estimate=50,
    )


def _question(qid: str) -> m_prop.AuthorQuestion:
    return m_prop.AuthorQuestion(
        id=qid, question="q?", purpose="opinion", required=True,
    )


def _proposal(**over: object) -> m_prop.Proposal:
    stmt = m_exp.ReportStatement(
        text="s", origin=m_exp.Origin.SOURCE, note_ids=["note_1"], unit_ids=["unit_1"],
    )
    base: dict[str, object] = {
        "id": "prop_1", "run_id": "run_1", "kind": "statistic",
        "source_agent": "scout", "title": "t", "pitch": "p",
        "what_was_found": [stmt], "connects_to_units": ["unit_1"],
        "message_ids": ["M1"], "media_work": None,
        "placements": [_placement("P1"), _placement("P2")],
        "modes": [_mode("M1"), _mode("M2")],
        "questions": [_question("q1"), _question("q2")],
        "risks": [], "grade_id": "gr_1", "status": "queued", "priority": 0.9,
    }
    base.update(over)
    return m_prop.Proposal.model_validate(base)


def test_proposal_roundtrips() -> None:
    assert roundtrip(_placement("P1")) == _placement("P1")
    assert roundtrip(_mode("M1")) == _mode("M1")
    assert roundtrip(_question("q1")) == _question("q1")
    assert roundtrip(_proposal()) == _proposal()
    dec = m_prop.ProposalDecision(
        proposal_id="prop_1", decision="accept", placement_id="P1", mode_id="M1",
        answers={"q1": "yes"}, author_notes="", reject_reason=None,
        decided_at=datetime(2026, 1, 1),
    )
    assert roundtrip(dec) == dec
    item = m_prop.IntegrationPlanItem(
        id="ip_1", proposal_id="prop_1", chapter_id="ch01",
        placement=_placement("P1"), mode=_mode("M1"),
        author_answers={"q1": "yes"}, evidence_ids=["ev_1"], status="planned",
    )
    assert roundtrip(item) == item


def test_proposal_requires_two_placements() -> None:
    with pytest.raises(ValidationError):
        _proposal(placements=[_placement("P1")])


def test_proposal_requires_two_modes() -> None:
    with pytest.raises(ValidationError):
        _proposal(modes=[_mode("M1")])


@pytest.mark.parametrize("n", [0, 1, 6])
def test_proposal_requires_two_to_five_questions(n: int) -> None:
    with pytest.raises(ValidationError):
        _proposal(questions=[_question(f"q{i}") for i in range(n)])


def test_rewrite_roundtrips() -> None:
    hunk = m_rw.RevisionHunk(
        id="hunk_1", revision_id="rev_1", unit_ids=["unit_1"],
        before="a", after="b", before_span=(0, 1), change_type="grammar",
        reason="r", agent="mechanic", origin=m_exp.Origin.SYSTEM, status="proposed",
    )
    assert roundtrip(hunk) == hunk
    rev = m_rw.Revision(
        id="rev_1", document_id="doc_1", chapter_id="ch01", pass_name="A",
        parent_revision_id=None, text_path="p", sha256="s", hunks=["hunk_1"],
        style_report_id=None, cross_check_report_id=None, gate_status="pending",
    )
    assert roundtrip(rev) == rev
    guide = m_rw.StyleGuide(
        version=1, source_hash="h", voice_summary="v", dos=["d"], donts=["x"],
        protected_terms=["p"], intentional_patterns=["i"],
        punctuation_habits={"em_dash": "frequent"}, person_and_address="first person",
        rhythm_targets={"mean": 12.0}, examples=["e"],
    )
    assert roundtrip(guide) == guide
    fp = m_rw.VoiceFingerprint(
        source="document", avg_sentence_len=12.0, sentence_len_stdev=3.0,
        type_token_ratio=0.5, punctuation_profile={}, person_ratio={},
        signature_phrases=[], llm_style_description="d",
    )
    assert roundtrip(fp) == fp
    sr = m_rw.StyleReport(
        id="sr_1", revision_id="rev_1", fingerprint_before=fp, fingerprint_after=fp,
        voice_similarity=0.9, per_hunk_similarity={"hunk_1": 0.9},
        protected_terms_intact=1.0, drift_notes=[], tone_shift={},
        verdict="pass", fix_requests=[],
    )
    assert roundtrip(sr) == sr
    item = m_rw.CrossCheckItem(id="cc_1", text="t", status="match")
    assert roundtrip(item) == item
    ccr = m_rw.CrossCheckReport(
        id="ccr_1", revision_id="rev_1", items=[item], pass_rate=1.0, verdict="pass",
    )
    assert roundtrip(ccr) == ccr
