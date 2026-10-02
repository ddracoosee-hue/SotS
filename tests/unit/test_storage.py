"""Storage tests (P01 T01.030-T01.035): schema, migrate, round-trips, files."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from sots.models.agents import (
    AgentCard,
    AgentCardPrompts,
    AgentGrading,
    AgentLimits,
    AgentRun,
    BudgetSlice,
)
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
from sots.models.document import Chunk, Document
from sots.models.enums import (
    Checkability,
    ClaimKind,
    ContentType,
    MediaKind,
    Severity,
    SourceClass,
    StageStatus,
    Stance,
    Verdict,
)
from sots.models.evidence import Evidence, FetchedDoc, SearchHit
from sots.models.expansion import (
    Concept,
    ConceptEdge,
    ConceptGraph,
    CriticScore,
    DeepResearchReport,
    ExpansionThread,
    IntegrationBrief,
    MarginNote,
    Origin,
    ReportSection,
    ReportStatement,
    ResearchBrief,
    ResearchNote,
)
from sots.models.grading import CriterionResult, GradeRecord, GraderHealth
from sots.models.learning import LearningChange, PromptTrial
from sots.models.legal import Authority, DefenseMemo, LegalIssue, Position
from sots.models.media import MediaCheck, MediaPoint, MediaWork
from sots.models.narrative import (
    CoreMessage,
    DriftReport,
    MessageMapping,
    VoiceComparison,
    VoiceFingerprint,
)
from sots.models.profile import AuthorProfile, BookProfile, ChapterBrief
from sots.models.proposal import (
    AuthorQuestion,
    IntegrationMode,
    IntegrationPlanItem,
    PlacementOption,
    Proposal,
    ProposalDecision,
)
from sots.models.psyche import EngineFinding, Synthesis
from sots.models.rewrite import (
    CrossCheckItem,
    CrossCheckReport,
    Revision,
    RevisionHunk,
    StyleGuide,
    StyleReport,
)
from sots.models.run import ChapterState, LLMCall, Run
from sots.models.shadow import RubricScore, ShadowItem, ShadowReport
from sots.models.unit import Unit
from sots.models.verdict import (
    DiscoveryNote,
    RuleCheck,
    SpecialistFindings,
    VerdictRecord,
)
from sots.storage import db as storage_db
from sots.storage import files as storage_files
from sots.storage import repo

TS = datetime(2026, 1, 1, 12, 0, 0)
DAY = date(2025, 6, 1)


@pytest.fixture()
def conn(tmp_path: Path) -> Any:
    connection = storage_db.connect(tmp_path / "test.db")
    storage_db.migrate(connection)
    yield connection
    connection.close()


@pytest.fixture()
def mem_conn() -> Any:
    connection = storage_db.connect(":memory:")
    connection.executescript(storage_db.SCHEMA_SQL.read_text(encoding="utf-8"))
    yield connection
    connection.close()


def make_fingerprint() -> VoiceFingerprint:
    return VoiceFingerprint(
        source="voice_corpus",
        avg_sentence_len=14.5,
        sentence_len_stdev=5.2,
        type_token_ratio=0.42,
        punctuation_profile={"comma": 30.1},
        person_ratio={"first": 0.7, "second": 0.1, "third": 0.2},
        signature_phrases=["here is the thing"],
        llm_style_description="plain and direct",
    )


def make_media_work() -> MediaWork:
    return MediaWork(
        id="work_1",
        kind=MediaKind.BOOK,
        title="Example Book",
        creators=["Jane Author"],
        year=1999,
        external_ids={"openlibrary": "OL1"},
        resolved=True,
    )


def make_concept() -> Concept:
    return Concept(
        id="concept_1",
        label="grace",
        definition="unearned favor",
        unit_ids=["unit_1"],
        chapter_ids=["ch01"],
        message_ids=["M1"],
        maturity="seed",
    )


def make_edge() -> ConceptEdge:
    return ConceptEdge(
        source_id="concept_1",
        target_id="concept_2",
        relation="causes",
        rationale="because",
        unit_ids=["unit_1"],
        inferred=False,
    )


def make_statement() -> ReportStatement:
    return ReportStatement(
        text="a sourced claim", origin=Origin.SOURCE, note_ids=["rn_1"], unit_ids=[]
    )


def make_section() -> ReportSection:
    return ReportSection(heading="Findings", statements=[make_statement()])


def make_placement(i: int) -> PlacementOption:
    return PlacementOption(
        id=f"place_{i}",
        location="after_unit",
        anchor_unit_id="unit_1",
        chapter_id="ch01",
        rationale="fits here",
        preview_outline=["a", "b"],
    )


def make_mode(i: int) -> IntegrationMode:
    return IntegrationMode(
        id=f"mode_{i}", mode="brief_mention", description="a short mention",
        word_estimate=50,
    )


def make_question(i: int) -> AuthorQuestion:
    return AuthorQuestion(
        id=f"q_{i}", question="Did this happen?", purpose="memory", required=True
    )


def make_proposal() -> Proposal:
    return Proposal(
        id="prop_1",
        run_id="run_1",
        kind="expansion",
        source_agent="explorer",
        title="Add a study",
        pitch="A strong study fits here.",
        what_was_found=[make_statement()],
        connects_to_units=["unit_1"],
        message_ids=["M1"],
        media_work=None,
        placements=[make_placement(1), make_placement(2)],
        modes=[make_mode(1), make_mode(2)],
        questions=[make_question(1), make_question(2)],
        risks=["too long"],
        grade_id="grade_1",
        status="queued",
        priority=1.0,
    )


CASES: list[dict[str, Any]] = []


def _case(
    label: str,
    make: Callable[[], Any],
    save: Callable[..., Any],
    get: Callable[..., Any],
    list_fn: Callable[..., Any],
    **list_filter: Any,
) -> dict[str, Any]:
    case = {
        "label": label, "make": make, "save": save, "get": get,
        "list": list_fn, "filter": list_filter,
    }
    CASES.append(case)
    return case


_case(
    "document",
    lambda: Document(
        id="doc_1", source_path="draft/ch01.md", inbox_path="data/inbox/a.md",
        sha256="0" * 64, title="Ch 1", chapter_id="ch01", char_count=100,
        word_count=20, ingested_at=TS,
    ),
    repo.save_document, repo.get_document, repo.list_documents, chapter_id="ch01",
)
_case(
    "chunk",
    lambda: Chunk(
        id="chk_1", document_id="doc_1", index=0, start_char=0, end_char=500,
        token_estimate=120,
    ),
    repo.save_chunk, repo.get_chunk, repo.list_chunks, document_id="doc_1",
)
_case(
    "unit",
    lambda: Unit(
        id="unit_1", document_id="doc_1", chunk_id="chk_1", run_id="run_1", order=0,
        text="The author wrote this.", start_char=0, end_char=22,
        content_type=ContentType.FACTUAL_CLAIM, claim_kind=ClaimKind.STATISTIC,
        checkability=Checkability.CHECKABLE, entities=["World Bank"],
        normalized_claim="neutral", classify_confidence=0.9, block=2,
        prompt_id="ch01.B2.P1", anchor_ids=["a1"], labeled_by="model",
        revision_offsets={"rev_1": (0, 22)},
    ),
    repo.save_unit, repo.get_unit, repo.list_units, run_id="run_1",
)
_case(
    "evidence",
    lambda: Evidence(
        id="ev_1", unit_id="unit_1", url="https://example.gov/data", title="Data",
        publisher="Example", published_date=DAY, accessed_at=TS,
        source_class=SourceClass.PRIMARY_RECORD, tier=1, excerpt="verbatim",
        excerpt_match_score=100.0, stance=Stance.SUPPORTS, fetcher="web",
        content_hash="abc123",
    ),
    repo.save_evidence, repo.get_evidence, repo.list_evidence, unit_id="unit_1",
)
_case(
    "fetched_doc",
    lambda: FetchedDoc(
        url="https://example.com/page", title="Page", publisher=None,
        published_date=None, text="readable", content_hash="h1", fetcher="web",
    ),
    repo.save_fetched_doc, repo.get_fetched_doc, repo.list_fetched_docs,
    fetcher="web",
)
_case(
    "search_hit",
    lambda: SearchHit(url="https://example.com", title="T", snippet="s", rank=1),
    repo.save_search_hit, repo.get_search_hit, repo.list_search_hits, rank=1,
)
_case(
    "verdict",
    lambda: VerdictRecord(
        id="vd_1", unit_id="unit_1", run_id="run_1",
        proposed_verdict=Verdict.TRUE, final_verdict=Verdict.MOSTLY_TRUE,
        truth_basis=SourceClass.ACADEMIC, confidence=0.75, evidence_ids=["ev_1"],
        researcher_summary="s", skeptic_objections=["o"],
        adjudicator_reasoning="r",
        rule_checks=[RuleCheck(rule_id="VR-GEN-02", passed=True, cap=None, note="ok")],
        what_is_accurate="year", what_is_off="pct", suggested_correction="w",
        claim_specific={"v": 1}, epistemic_tier="PT", tier_claimed_by_author=None,
    ),
    repo.save_verdict, repo.get_verdict, repo.list_verdicts, run_id="run_1",
)
_case(
    "discovery_note",
    lambda: DiscoveryNote(
        id="disc_1", unit_id="unit_1", agent="stats", kind="newer_data",
        summary="newer data", evidence_id="ev_1", why_interesting="current",
    ),
    repo.save_discovery_note, repo.get_discovery_note, repo.list_discovery_notes,
    unit_id="unit_1",
)
_case(
    "specialist_findings",
    lambda: SpecialistFindings(
        unit_id="unit_1", specialist="stats", evidence_ids=["ev_1"],
        claim_specific={"v": 40},
    ),
    repo.save_specialist_findings, repo.get_specialist_findings,
    repo.list_specialist_findings, specialist="stats",
)
_case(
    "media_work",
    make_media_work,
    repo.save_media_work, repo.get_media_work, repo.list_media_works,
    kind=MediaKind.BOOK,
)
_case(
    "media_check",
    lambda: MediaCheck(
        id="mc_1", unit_id="unit_1", run_id="run_1", work=make_media_work(),
        points=[
            MediaPoint(
                statement="the hero dies", point_type="plot_fact",
                accuracy="accurate", correction=None, evidence_ids=["ev_1"],
            )
        ],
        author_reading="about hope", established_readings=["creator interview"],
        interpretation_status="supported_reading", message_alignment=0.8,
        use_in_book_note="serves the point",
    ),
    repo.save_media_check, repo.get_media_check, repo.list_media_checks,
    run_id="run_1",
)
_case(
    "engine_finding",
    lambda: EngineFinding(
        id="pf_1", run_id="run_1", engine="emotion", finding_type="flat_arc",
        unit_ids=["unit_1"], summary="s", detail="d", confidence=0.6,
        severity=Severity.LOW, responds_to=[], question_for_author=None,
    ),
    repo.save_engine_finding, repo.get_engine_finding, repo.list_engine_findings,
    run_id="run_1",
)
_case(
    "synthesis",
    lambda: Synthesis(
        run_id="run_1", agreements=["a"], tensions=["t"], top_insights=["i"],
        finding_ids=["pf_1"],
    ),
    repo.save_synthesis, repo.get_synthesis, repo.list_syntheses, run_id="run_1",
)
_case(
    "core_message",
    lambda: CoreMessage(
        id="M1", level="book", chapter_id=None, statement="grace wins", priority=1
    ),
    repo.save_core_message, repo.get_core_message, repo.list_core_messages,
    level="book",
)
_case(
    "message_mapping",
    lambda: MessageMapping(
        unit_id="unit_1", message_id="M1", role="states", strength=0.9
    ),
    repo.save_message_mapping, repo.get_message_mapping, repo.list_message_mappings,
    unit_id="unit_1",
)
_case(
    "drift_report",
    lambda: DriftReport(
        run_id="run_1", document_id="doc_1", coverage={"M1": 0.8},
        unmapped_ratio=0.2, drift_segments=[(0, 3)], missing_messages=[],
        flow_breaks=["unit_9"],
    ),
    repo.save_drift_report, repo.get_drift_report, repo.list_drift_reports,
    run_id="run_1",
)
_case(
    "voice_fingerprint",
    make_fingerprint,
    repo.save_voice_fingerprint, repo.get_voice_fingerprint,
    repo.list_voice_fingerprints, source="voice_corpus",
)
_case(
    "voice_comparison",
    lambda: VoiceComparison(
        run_id="run_1", document_id="doc_1", similarity=0.9, deviations=["d"],
        off_voice_unit_ids=["unit_9"],
    ),
    repo.save_voice_comparison, repo.get_voice_comparison,
    repo.list_voice_comparisons, run_id="run_1",
)
_case(
    "shadow_report",
    lambda: ShadowReport(
        id="sh_1", run_id="run_1", document_id="doc_1",
        items=[
            ShadowItem(
                category="avoidance", unit_ids=["unit_1"], observation="o",
                question_for_author="q", severity=Severity.MEDIUM,
            )
        ],
        scores=[
            RubricScore(
                criterion_id="c1", score=4, measured_value=0.8, target=0.7, met=True,
                justification="j", unit_ids=["unit_1"],
            )
        ],
        overall=4.0, goals_met=1, goals_total=1, trend_vs_previous={"c1": 0.5},
    ),
    repo.save_shadow_report, repo.get_shadow_report, repo.list_shadow_reports,
    run_id="run_1",
)
_case(
    "author_profile",
    lambda: AuthorProfile(
        name_or_pen_name="Jane", background="teacher", why_this_book="help",
        lived_experience_areas=["teaching"], sensitive_topics=["grief"],
        values=["honesty"], known_biases_self_reported=["optimism"],
    ),
    repo.save_author_profile, repo.get_author_profile, repo.list_author_profiles,
    name_or_pen_name="Jane",
)
_case(
    "book_profile",
    lambda: BookProfile(
        working_title="Grace", genre="self_help_reflective", premise="p",
        target_reader="seekers", promise_to_reader="hope", tone_goals=["warm"],
        out_of_scope=["politics"], media_exclusions=["horror"],
    ),
    repo.save_book_profile, repo.get_book_profile, repo.list_book_profiles,
    genre="self_help_reflective",
)
_case(
    "chapter_brief",
    lambda: ChapterBrief(
        chapter_id="ch01", title="Begin", purpose="hook", key_messages=["m"],
        planned_stories=["s"], planned_references=["r"], reader_takeaway="hope",
        raw_brief="raw", reader_journey=None,
    ),
    repo.save_chapter_brief, repo.get_chapter_brief, repo.list_chapter_briefs,
    chapter_id="ch01",
)
_case(
    "run",
    lambda: Run(
        id="run_1", document_ids=["doc_1"], started_at=TS, finished_at=None,
        stage_status={"ingest": StageStatus.DONE}, budget_tokens=1000,
        used_tokens=10, cost_estimate=0.01, config_snapshot={"k": "v"},
    ),
    repo.save_run, repo.get_run, repo.list_runs, id="run_1",
)
_case(
    "llm_call",
    lambda: LLMCall(
        id="call_1", run_id="run_1", task="verify.skeptic", provider="x",
        model="m1", prompt_id="p1", prompt_version=1, input_hash="h",
        input_tokens=10, output_tokens=20, cost_estimate=0.01, latency_ms=100,
        status="ok", created_at=TS,
    ),
    repo.save_llm_call, repo.get_llm_call, repo.list_llm_calls, run_id="run_1",
)
_case(
    "chapter_state",
    lambda: ChapterState(
        chapter_id="ch01", act=1, gate_status={"ingest": "passed"},
        blocked_reasons=[],
    ),
    repo.save_chapter_state, repo.get_chapter_state, repo.list_chapter_states,
    chapter_id="ch01",
)
_case(
    "concept",
    make_concept,
    repo.save_concept, repo.get_concept, repo.list_concepts, maturity="seed",
)
_case(
    "concept_edge",
    make_edge,
    repo.save_concept_edge, repo.get_concept_edge, repo.list_concept_edges,
    relation="causes",
)
_case(
    "concept_graph",
    lambda: ConceptGraph(
        run_id="run_1", concepts=[make_concept()], edges=[make_edge()],
        hubs=["concept_1"], bridges=[], orphans=[],
    ),
    repo.save_concept_graph, repo.get_concept_graph, repo.list_concept_graphs,
    run_id="run_1",
)
_case(
    "expansion_thread",
    lambda: ExpansionThread(
        id="thread_1", title="Grace in history", kind="deepen",
        concept_ids=["concept_1"], message_ids=["M1"], rationale="r",
        estimated_tokens=500, status="proposed", critic_score=None,
    ),
    repo.save_expansion_thread, repo.get_expansion_thread,
    repo.list_expansion_threads, status="proposed",
)
_case(
    "research_brief",
    lambda: ResearchBrief(
        thread_id="thread_1", central_question="q", why_it_matters="w",
        author_starting_point=["a"], sub_questions=["s1"], must_find=["statistic"],
        exclusions=["e"], max_depth=3, max_sources=10,
    ),
    repo.save_research_brief, repo.get_research_brief, repo.list_research_briefs,
    thread_id="thread_1",
)
_case(
    "research_note",
    lambda: ResearchNote(
        id="rn_1", thread_id="thread_1", sub_question="s1", claim="c",
        evidence_id="ev_1", depth=1, novelty=0.5, leads=["l1"],
    ),
    repo.save_research_note, repo.get_research_note, repo.list_research_notes,
    thread_id="thread_1",
)
_case(
    "deep_research_report",
    lambda: DeepResearchReport(
        id="rep_1", thread_id="thread_1", title="Grace",
        executive_summary=[make_statement()], sections=[make_section()],
        counter_perspectives=make_section(), connections_to_author_text=make_section(),
        new_concepts=[], open_questions=["o"], source_mix={"academic": 2},
        saturation_curve=[0.5, 0.8],
    ),
    repo.save_deep_research_report, repo.get_deep_research_report,
    repo.list_deep_research_reports, thread_id="thread_1",
)
_case(
    "margin_note",
    lambda: MarginNote(
        id="mn_1", unit_id="unit_1", kind="connects_to", text="see ch2",
        origin=Origin.SYSTEM, links=["unit_2"], status="open",
    ),
    repo.save_margin_note, repo.get_margin_note, repo.list_margin_notes,
    status="open",
)
_case(
    "integration_brief",
    lambda: IntegrationBrief(
        id="ib_1", report_id="rep_1", chapter_id="ch01",
        placements=[{"at": "unit_1"}], new_message_candidates=[],
        restructure_suggestions=[], questions_for_author=[], risks=[],
    ),
    repo.save_integration_brief, repo.get_integration_brief,
    repo.list_integration_briefs, chapter_id="ch01",
)
_case(
    "critic_score",
    lambda: CriticScore(
        target_id="thread_1", relevance=0.8, grounding=0.7, novelty=0.6,
        voice_respect=0.9, balance=0.7, verdict="accept", reasons=["solid"],
    ),
    repo.save_critic_score, repo.get_critic_score, repo.list_critic_scores,
    verdict="accept",
)
_case(
    "agent_card",
    lambda: AgentCard(
        name="skeptic", team="verify", role="challenge claims",
        prompts=AgentCardPrompts(system="sys", step="step"), output_model="Finding",
        routing_task="verify.skeptic", tools=["search"], internet=True,
        limits=AgentLimits(max_steps=5, max_tokens=2000, timeout_s=60, max_retries=2),
        grading=AgentGrading(rubric="r1"), failsafes=["F01", "F07"],
        on_failure="dead_letter",
    ),
    repo.save_agent_card, repo.get_agent_card, repo.list_agent_cards, team="verify",
)
_case(
    "agent_run",
    lambda: AgentRun(
        id="ar_1", run_id="run_1", agent="skeptic", team="verify", act="1",
        started_at=TS, finished_at=None, steps=3, tokens_in=100, tokens_out=50,
        cost=0.02, status="ok", failure_code=None, grade_attempts=1,
        final_grade=None, checkpoint_key="ckpt_1",
    ),
    repo.save_agent_run, repo.get_agent_run, repo.list_agent_runs, run_id="run_1",
)
_case(
    "budget_slice",
    lambda: BudgetSlice(
        scope="run_1", tokens_allowed=1000, tokens_used=10, cost_allowed=1.0,
        cost_used=0.01,
    ),
    repo.save_budget_slice, repo.get_budget_slice, repo.list_budget_slices,
    scope="run_1",
)
_case(
    "grade_record",
    lambda: GradeRecord(
        id="grade_1", artifact_type="proposal", artifact_id="prop_1", attempt=1,
        rubric_id="r1", rubric_version=2,
        criteria=[
            CriterionResult(
                id="c1", type="judged", score=0.8, floor=0.5, evidence="e",
                judges={"j1": 0.8},
            )
        ],
        score=0.8, passed=True, feedback_for_generator=[], created_at=TS,
    ),
    repo.save_grade_record, repo.get_grade_record, repo.list_grade_records,
    artifact_id="prop_1",
)
_case(
    "grader_health",
    lambda: GraderHealth(
        window_grades=50, first_attempt_pass_rate=0.7, author_reject_rate=0.1,
        pass_within_max_rate=0.95, tiebreak_rate=0.05, too_lenient=False,
        too_strict=False, judge_disagreement=False,
        top_rejection_reasons=["thin evidence"],
    ),
    repo.save_grader_health, repo.get_grader_health, repo.list_grader_health,
    window_grades=50,
)
_case(
    "proposal",
    make_proposal,
    repo.save_proposal, repo.get_proposal, repo.list_proposals, run_id="run_1",
)
_case(
    "proposal_decision",
    lambda: ProposalDecision(
        proposal_id="prop_1", decision="accept", placement_id="place_1",
        mode_id="mode_1", answers={"q_1": "yes"}, author_notes="go",
        reject_reason=None, decided_at=TS,
    ),
    repo.save_proposal_decision, repo.get_proposal_decision,
    repo.list_proposal_decisions, proposal_id="prop_1",
)
_case(
    "integration_plan_item",
    lambda: IntegrationPlanItem(
        id="plan_1", proposal_id="prop_1", chapter_id="ch01",
        placement=make_placement(1), mode=make_mode(1),
        author_answers={"q_1": "yes"}, evidence_ids=["ev_1"], status="planned",
    ),
    repo.save_integration_plan_item, repo.get_integration_plan_item,
    repo.list_integration_plan_items, chapter_id="ch01",
)
_case(
    "revision_hunk",
    lambda: RevisionHunk(
        id="hunk_1", revision_id="rev_1", unit_ids=["unit_1"], before="teh",
        after="the", before_span=(0, 3), change_type="spelling", reason="typo",
        agent="copyedit", evidence_ids=[], legal_issue_ids=[],
        audience_brief_id=None, origin=Origin.SYSTEM, status="proposed",
    ),
    repo.save_revision_hunk, repo.get_revision_hunk, repo.list_revision_hunks,
    revision_id="rev_1",
)
_case(
    "revision",
    lambda: Revision(
        id="rev_1", document_id="doc_1", chapter_id="ch01", pass_name="A",
        parent_revision_id=None, text_path="revisions/rev_1/text.md", sha256="1" * 64,
        hunks=["hunk_1"], style_report_id=None, cross_check_report_id=None,
        gate_status="pending",
    ),
    repo.save_revision, repo.get_revision, repo.list_revisions, document_id="doc_1",
)
_case(
    "style_guide",
    lambda: StyleGuide(
        version=1, source_hash="h", voice_summary="plain", dos=["short"],
        donts=["purple"], protected_terms=["grace"], intentional_patterns=["frag"],
        punctuation_habits={"comma": "often"}, person_and_address="second",
        rhythm_targets={"short_share": 0.6}, examples=["ex"],
    ),
    repo.save_style_guide, repo.get_style_guide, repo.list_style_guides, version=1,
)
_case(
    "style_report",
    lambda: StyleReport(
        id="sr_1", revision_id="rev_1", fingerprint_before=make_fingerprint(),
        fingerprint_after=make_fingerprint(), voice_similarity=0.95,
        per_hunk_similarity={"hunk_1": 0.9}, protected_terms_intact=1.0,
        drift_notes=[], tone_shift={}, verdict="pass", fix_requests=[],
    ),
    repo.save_style_report, repo.get_style_report, repo.list_style_reports,
    revision_id="rev_1",
)
_case(
    "cross_check_report",
    lambda: CrossCheckReport(
        id="cc_1", revision_id="rev_1",
        items=[CrossCheckItem(id="cci_1", text="claim", status="match")],
        pass_rate=1.0, verdict="pass", notes=[],
    ),
    repo.save_cross_check_report, repo.get_cross_check_report,
    repo.list_cross_check_reports, revision_id="rev_1",
)
_case(
    "persona",
    lambda: Persona(
        id="per_1", name="Maya", cohort="millennial", age=34,
        life_stage="parent", region="US", background_notes="b", reading_habits="r",
        need_for_cognition="high", current_season="busy", skepticism="medium",
        values=["family"], what_would_make_them_close_the_book="preaching",
    ),
    repo.save_persona, repo.get_persona, repo.list_personas, cohort="millennial",
)
_case(
    "mechanics_finding",
    lambda: MechanicsFinding(
        id="mf_1", analyst="pacing", revision_id="rev_1", unit_ids=["unit_1"],
        metric=None, value=None, threshold=None, issue="drag", suggestion="cut",
        severity=Severity.INFO,
    ),
    repo.save_mechanics_finding, repo.get_mechanics_finding,
    repo.list_mechanics_findings, revision_id="rev_1",
)
_case(
    "persona_reaction",
    lambda: PersonaReaction(
        id="pr_1", persona_id="per_1", sample=1, revision_id="rev_1",
        section_id="sec_1", first_impression="warm", felt=["seen"],
        recognition=8.0, felt_judged=1.0, curiosity=7.0, absorption=7.5,
        insight=6.0, agency=6.5, preachiness=2.0, credibility=8.0,
        intellectual_respect=8.0, relatability=7.0, would_continue=8.0,
        would_share=6.0,
        confusing_parts=[QuoteRef(unit_id="unit_1", quote="huh?", note="")],
        cringe_parts=[],
        strongest_line=QuoteRef(unit_id="unit_1", quote="grace wins", note="kept"),
        takeaway_in_own_words="hope", disagreements=[],
        question_for_author=None,
    ),
    repo.save_persona_reaction, repo.get_persona_reaction,
    repo.list_persona_reactions, revision_id="rev_1",
)
_case(
    "audience_scorecard",
    lambda: AudienceScorecard(
        id="sc_1", revision_id="rev_1", metric_means={"insight": 6.0},
        cohort_means={"millennial": {"insight": 6.0}}, metric_sd={"insight": 1.0},
        metric_min={"insight": 4.0}, metric_max={"insight": 8.0},
        message_reception_rate=0.8, journey_curve={"millennial": [5.0, 7.0]},
        hotspots=["unit_1"], strong_lines=["grace wins"],
    ),
    repo.save_audience_scorecard, repo.get_audience_scorecard,
    repo.list_audience_scorecards, revision_id="rev_1",
)
_case(
    "audience_brief",
    lambda: AudienceBrief(
        id="ab_1", revision_id="rev_1", scorecard_id="sc_1",
        priorities=[
            BriefItem(
                unit_ids=["unit_1"], problem="p", evidence="e", direction="cut",
                protect=["grace"],
            )
        ],
        do_not_touch=["unit_2"], voice_cautions=["keep plain"],
    ),
    repo.save_audience_brief, repo.get_audience_brief, repo.list_audience_briefs,
    revision_id="rev_1",
)
_case(
    "calibration",
    lambda: CalibrationRecord(
        id="cal_1", metric="insight", cohort="millennial", synthetic_mean=6.0,
        real_mean=5.5, bias=0.5, correlation=None, real_respondents=10,
        unreliable=False,
    ),
    repo.save_calibration_record, repo.get_calibration_record,
    repo.list_calibration_records, metric="insight",
)
_case(
    "playbook",
    lambda: PlaybookEntry(
        technique="shorten", cohort="millennial", metric="absorption",
        alpha=3.0, beta=1.0, trials=2,
    ),
    repo.save_playbook_entry, repo.get_playbook_entry, repo.list_playbook_entries,
    technique="shorten",
)
_case(
    "legal_issue",
    lambda: LegalIssue(
        id="li_1", run_id="run_1", revision_id="rev_1", unit_ids=["unit_1"],
        issue_types=["defamation"], persons_involved=[{"name": "X"}],
        preliminary_risk=Severity.LOW, assigned_counsel=["counsel_a"],
        status="open",
    ),
    repo.save_legal_issue, repo.get_legal_issue, repo.list_legal_issues,
    run_id="run_1",
)
_case(
    "position",
    lambda: Position(
        id="pos_1", issue_id="li_1", counsel="counsel_a", round=1,
        stance="safe_with_edits", risk=Severity.LOW, argument="arg",
        authorities=[
            Authority(
                kind="case", citation="X v Y", jurisdiction="US",
                evidence_id="ev_1",
            )
        ],
        proposed_edits=[{"at": "unit_1"}], rebuttals=[], argument_score=None,
    ),
    repo.save_position, repo.get_position, repo.list_positions, issue_id="li_1",
)
_case(
    "defense_memo",
    lambda: DefenseMemo(
        id="dm_1", issue_id="li_1", text_position="para 3",
        defense_basis=["truth_substantial_truth"], argument="true",
        required_edits=[], residual_risk=Severity.LOW, answered_dissents=[],
        endorsements={"counsel_a": "endorse"}, grade_id="grade_1",
        needs_licensed_attorney=False,
    ),
    repo.save_defense_memo, repo.get_defense_memo, repo.list_defense_memos,
    issue_id="li_1",
)
_case(
    "learning_change",
    lambda: LearningChange(
        id="lc_1", kind="prompt", target="verify.skeptic", before="old",
        after="new", evidence="trial", status="proposed", applied_at=None,
    ),
    repo.save_learning_change, repo.get_learning_change, repo.list_learning_changes,
    status="proposed",
)
_case(
    "prompt_trial",
    lambda: PromptTrial(
        id="pt_1", prompt_id="verify.skeptic", baseline_version=1,
        candidate_version=2, metric_deltas={"insight": 0.3},
        release_blocker_regressions=[], promoted=False,
    ),
    repo.save_prompt_trial, repo.get_prompt_trial, repo.list_prompt_trials,
    prompt_id="verify.skeptic",
)


CASE_IDS = [c["label"] for c in CASES]


def _get_args(saved: Any) -> tuple[Any, ...]:
    return saved if isinstance(saved, tuple) else (saved,)


def test_all_cases_registered() -> None:
    assert len(CASES) == 60, f"expected 60 persisted models, got {len(CASES)}"


@pytest.mark.parametrize("label", CASE_IDS)
def test_model_round_trip(conn: Any, label: str) -> None:
    case = next(c for c in CASES if c["label"] == label)
    instance = case["make"]()
    saved = case["save"](conn, instance)
    loaded = case["get"](conn, *_get_args(saved))
    assert loaded == instance
    assert loaded is not None
    assert instance in case["list"](conn)
    assert instance in case["list"](conn, **case["filter"])


def test_schema_applies_clean_to_empty_db() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(storage_db.SCHEMA_SQL.read_text(encoding="utf-8"))
        tables = {
            r[0]
            for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()
    for expected in (
        "documents", "units", "verdict_records", "summaries", "llm_calls", "cache",
        "dead_letters", "checkpoints", "events", "playbook", "calibration",
        "grader_health", "prompt_trials", "dialogues", "waivers", "chapter_state",
        "schema_version",
    ):
        assert expected in tables


def test_migrate_from_empty_then_noop(tmp_path: Path) -> None:
    connection = storage_db.connect(tmp_path / "m.db")
    try:
        expected = [int(p.name.split("_", 1)[0]) for p in storage_db.migration_files()]
        assert expected, "expected at least one migration file"
        assert storage_db.migrate(connection) == expected
        assert storage_db.applied_versions(connection) == expected
        assert storage_db.migrate(connection) == []
    finally:
        connection.close()


def test_connect_enables_pragmas(tmp_path: Path) -> None:
    connection = storage_db.connect(tmp_path / "p.db")
    try:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()


def test_double_save_upserts_one_row(conn: Any) -> None:
    doc = Document(
        id="doc_2", source_path="s", inbox_path="i", sha256="h", title="v1",
        chapter_id=None, char_count=1, word_count=1, ingested_at=TS,
    )
    repo.save_document(conn, doc)
    repo.save_document(conn, doc.model_copy(update={"title": "v2"}))
    rows = repo.list_documents(conn, id="doc_2")
    assert len(rows) == 1
    assert rows[0].title == "v2"


def test_idempotent_save_writes_once(conn: Any) -> None:
    doc = Document(
        id="doc_3", source_path="s", inbox_path="i", sha256="h", title="v1",
        chapter_id=None, char_count=1, word_count=1, ingested_at=TS,
    )
    assert repo.idempotent_save(conn, doc, "key-1") is True
    changed = doc.model_copy(update={"title": "v2"})
    assert repo.idempotent_save(conn, changed, "key-1") is False
    rows = repo.list_documents(conn, id="doc_3")
    assert len(rows) == 1
    assert rows[0].title == "v1"


def test_idempotent_save_rejects_unregistered_model(conn: Any) -> None:
    with pytest.raises(ValueError, match="no table registered"):
        repo.idempotent_save(
            conn, RuleCheck(rule_id="r", passed=True, cap=None, note="n"), "k"
        )


def test_get_missing_returns_none(conn: Any) -> None:
    assert repo.get_document(conn, "nope") is None
    assert repo.get_search_hit(conn, 424242) is None
    assert repo.get_concept_edge(conn, "a", "b", "causes") is None


def test_unknown_filter_raises(conn: Any) -> None:
    with pytest.raises(ValueError, match="unknown filter"):
        repo.list_documents(conn, bogus="x")


def test_json_helpers_round_trip() -> None:
    assert repo.from_json(repo.to_json({"a": [1, 2]})) == {"a": [1, 2]}
    assert repo.from_json(repo.to_json(None)) is None


def test_infra_tables_round_trip(conn: Any) -> None:
    repo.save_summary(
        conn, "sum_1", "researcher", {"text": "hi"}, run_id="run_1",
        unit_id="unit_1", status="ok",
    )
    summary = repo.get_summary(conn, "sum_1")
    assert summary is not None and summary["body"] == {"text": "hi"}
    assert repo.get_summary(conn, "missing") is None
    assert len(repo.list_summaries(conn, run_id="run_1")) == 1

    repo.cache_set(conn, "k", "v")
    assert repo.cache_get(conn, "k") == "v"
    assert repo.cache_get(conn, "missing") is None
    assert repo.cache_delete(conn, "k") is True
    assert repo.cache_delete(conn, "k") is False

    repo.save_dead_letter(
        conn, "skeptic", "verify", {"unit": "unit_1"}, "boom", run_id="run_1"
    )
    assert len(repo.list_dead_letters(conn, run_id="run_1")) == 1

    repo.save_checkpoint(conn, "ckpt", {"step": 3}, run_id="run_1")
    checkpoint = repo.get_checkpoint(conn, "ckpt")
    assert checkpoint is not None and checkpoint["state"] == {"step": 3}
    assert repo.get_checkpoint(conn, "missing") is None

    repo.append_event(conn, "unit.done", {"unit_id": "unit_1"}, run_id="run_1")
    assert len(repo.list_events(conn, run_id="run_1")) == 1

    repo.save_dialogue(
        conn, "dlg_1", [{"role": "author", "text": "hi"}], "open",
        run_id="run_1", proposal_id="prop_1",
    )
    dialogue = repo.get_dialogue(conn, "dlg_1")
    assert dialogue is not None and dialogue["turns"] == [{"role": "author", "text": "hi"}]

    repo.save_waiver(conn, "li_1", "author accepted", "author", run_id="run_1")
    assert len(repo.list_waivers(conn, run_id="run_1")) == 1


def test_snapshot_counts(conn: Any) -> None:
    counts = repo.snapshot_counts(conn, "run_1")
    assert counts["units"] == 0
    repo.save_unit(
        conn,
        Unit(
            id="unit_9", document_id="doc_1", chunk_id="chk_1", run_id="run_1",
            order=0, text="t", start_char=0, end_char=1,
        ),
    )
    repo.save_verdict(
        conn,
        VerdictRecord(
            id="vd_9", unit_id="unit_9", run_id="run_1",
            proposed_verdict=Verdict.TRUE, final_verdict=Verdict.TRUE,
            truth_basis=None, confidence=0.9, evidence_ids=[],
            researcher_summary="s", skeptic_objections=[],
            adjudicator_reasoning="r", rule_checks=[],
            what_is_accurate="all", what_is_off="", suggested_correction=None,
            claim_specific={},
        ),
    )
    repo.append_event(conn, "unit.done", {}, run_id="run_1")
    counts = repo.snapshot_counts(conn, "run_1")
    assert counts["units"] == 1
    assert counts["verdict_records"] == 1
    assert counts["events"] == 1
    assert counts["media_checks"] == 0
    assert "evidence" not in counts  # unit-scoped tables are not run-counted
    other = repo.snapshot_counts(conn, "run_other")
    assert other["units"] == 0


def test_atomic_write_round_trip(tmp_path: Path) -> None:
    target = storage_files.inbox_path(tmp_path, "doc.md")
    assert target.parent.name == "inbox"
    storage_files.atomic_write_text(target, "hello")
    assert storage_files.read_text(target) == "hello"
    storage_files.atomic_write_bytes(target, b"updated")
    assert storage_files.read_bytes(target) == b"updated"
    assert storage_files.revision_path(tmp_path, "rev_1").parent.name == "rev_1"
    assert storage_files.export_path(tmp_path, "out.md").parent.name == "exports"


def test_interrupted_write_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "exports" / "out.md"

    def _boom(_src: str, _dst: str) -> None:
        raise RuntimeError("crash mid-rename")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(RuntimeError, match="crash"):
        storage_files.atomic_write_text(target, "partial?")
    assert not target.exists()
    leftovers = list(target.parent.iterdir()) if target.parent.exists() else []
    assert leftovers == []

