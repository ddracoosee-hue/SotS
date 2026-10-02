"""Table specs for storage/repo (W0 split of repo.py)."""

from __future__ import annotations

from pydantic import BaseModel

from sots.models.agents import AgentCard, AgentRun, BudgetSlice
from sots.models.audience import (
    AudienceBrief,
    AudienceScorecard,
    CalibrationRecord,
    MechanicsFinding,
    Persona,
    PersonaReaction,
    PlaybookEntry,
)
from sots.models.cache import CacheEntry
from sots.models.document import Chunk, Document, SupplementDoc
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
    ResearchBrief,
    ResearchNote,
)
from sots.models.grading import GradeRecord, GraderHealth
from sots.models.learning import LearningChange, PromptTrial
from sots.models.legal import DefenseMemo, LegalIssue, Position
from sots.models.media import MediaCheck, MediaWork
from sots.models.narrative import (
    CoreMessage,
    DriftReport,
    MessageMapping,
    VoiceComparison,
    VoiceFingerprint,
)
from sots.models.profile import AuthorProfile, BookProfile, ChapterBrief
from sots.models.proposal import IntegrationPlanItem, Proposal, ProposalDecision
from sots.models.psyche import EngineFinding, Synthesis
from sots.models.rewrite import CrossCheckReport, Revision, RevisionHunk, StyleGuide, StyleReport
from sots.models.run import ChapterState, LLMCall, Run
from sots.models.shadow import ShadowReport
from sots.models.unit import Unit
from sots.models.verdict import DiscoveryNote, SpecialistFindings, VerdictRecord
from sots.storage.repo._core import _Spec

_DOCUMENTS = _Spec("documents", Document, ("id",))
_CHUNKS = _Spec("chunks", Chunk, ("id",))
_UNITS = _Spec(
    "units", Unit, ("id",), frozenset({"entities", "anchor_ids", "revision_offsets"})
)
_EVIDENCE = _Spec("evidence", Evidence, ("id",))
_FETCHED_DOCS = _Spec("fetched_docs", FetchedDoc, ("url",))
_SUPPLEMENT_DOCS = _Spec("supplement_docs", SupplementDoc, ("path",))
_SEARCH_HITS = _Spec("search_hits", SearchHit, ())
_VERDICTS = _Spec(
    "verdict_records",
    VerdictRecord,
    ("id",),
    frozenset({"evidence_ids", "skeptic_objections", "rule_checks", "claim_specific"}),
)
_DISCOVERY_NOTES = _Spec("discovery_notes", DiscoveryNote, ("id",))
_SPECIALIST_FINDINGS = _Spec(
    "specialist_findings",
    SpecialistFindings,
    ("unit_id", "specialist"),
    frozenset({"evidence_ids", "claim_specific"}),
)
_MEDIA_WORKS = _Spec(
    "media_works", MediaWork, ("id",), frozenset({"creators", "external_ids"})
)
_MEDIA_CHECKS = _Spec(
    "media_checks",
    MediaCheck,
    ("id",),
    frozenset({"work", "points", "established_readings"}),
)
_ENGINE_FINDINGS = _Spec(
    "engine_findings", EngineFinding, ("id",), frozenset({"unit_ids", "responds_to"})
)
_SYNTHESES = _Spec(
    "syntheses",
    Synthesis,
    ("run_id",),
    frozenset({"agreements", "tensions", "top_insights", "finding_ids"}),
)
_CORE_MESSAGES = _Spec("core_messages", CoreMessage, ("id",))
_MESSAGE_MAPPINGS = _Spec("message_mappings", MessageMapping, ("unit_id",))
_DRIFT_REPORTS = _Spec(
    "drift_reports",
    DriftReport,
    ("run_id", "document_id"),
    frozenset({"coverage", "drift_segments", "missing_messages", "flow_breaks"}),
)
_VOICE_FINGERPRINTS = _Spec(
    "voice_fingerprints",
    VoiceFingerprint,
    (),
    frozenset({"punctuation_profile", "person_ratio", "signature_phrases"}),
)
_VOICE_COMPARISONS = _Spec(
    "voice_comparisons",
    VoiceComparison,
    ("run_id", "document_id"),
    frozenset({"deviations", "off_voice_unit_ids"}),
)
_SHADOW_REPORTS = _Spec(
    "shadow_reports",
    ShadowReport,
    ("id",),
    frozenset({"items", "scores", "trend_vs_previous"}),
)
_AUTHOR_PROFILES = _Spec(
    "author_profiles",
    AuthorProfile,
    (),
    frozenset(
        {
            "lived_experience_areas",
            "sensitive_topics",
            "values",
            "known_biases_self_reported",
        }
    ),
)
_BOOK_PROFILES = _Spec(
    "book_profiles",
    BookProfile,
    (),
    frozenset({"tone_goals", "out_of_scope", "media_exclusions"}),
)
_CHAPTER_BRIEFS = _Spec(
    "chapter_briefs",
    ChapterBrief,
    ("chapter_id",),
    frozenset({"key_messages", "planned_stories", "planned_references"}),
)
_RUNS = _Spec(
    "runs",
    Run,
    ("id",),
    frozenset({"document_ids", "stage_status", "config_snapshot"}),
)
_LLM_CALLS = _Spec("llm_calls", LLMCall, ("id",))
_CACHE = _Spec("cache", CacheEntry, ("key",))
_CHAPTER_STATE = _Spec(
    "chapter_state", ChapterState, ("chapter_id",), frozenset({"gate_status", "blocked_reasons"})
)
_CONCEPTS = _Spec(
    "concepts", Concept, ("id",), frozenset({"unit_ids", "chapter_ids", "message_ids"})
)
_CONCEPT_EDGES = _Spec(
    "concept_edges", ConceptEdge, ("source_id", "target_id", "relation"),
    frozenset({"unit_ids"}),
)
_CONCEPT_GRAPHS = _Spec(
    "concept_graphs",
    ConceptGraph,
    ("run_id",),
    frozenset({"concepts", "edges", "hubs", "bridges", "orphans"}),
)
_EXPANSION_THREADS = _Spec(
    "expansion_threads",
    ExpansionThread,
    ("id",),
    frozenset({"concept_ids", "message_ids"}),
)
_RESEARCH_BRIEFS = _Spec(
    "research_briefs",
    ResearchBrief,
    ("thread_id",),
    frozenset({"author_starting_point", "sub_questions", "must_find", "exclusions"}),
)
_RESEARCH_NOTES = _Spec("research_notes", ResearchNote, ("id",), frozenset({"leads"}))
_DEEP_REPORTS = _Spec(
    "deep_research_reports",
    DeepResearchReport,
    ("id",),
    frozenset(
        {
            "executive_summary",
            "sections",
            "counter_perspectives",
            "connections_to_author_text",
            "new_concepts",
            "open_questions",
            "source_mix",
            "saturation_curve",
        }
    ),
)
_MARGIN_NOTES = _Spec("margin_notes", MarginNote, ("id",), frozenset({"links"}))
_INTEGRATION_BRIEFS = _Spec(
    "integration_briefs",
    IntegrationBrief,
    ("id",),
    frozenset(
        {
            "placements",
            "new_message_candidates",
            "restructure_suggestions",
            "questions_for_author",
            "risks",
        }
    ),
)
_CRITIC_SCORES = _Spec(
    "critic_scores", CriticScore, ("target_id",), frozenset({"reasons"})
)
_AGENT_CARDS = _Spec(
    "agent_cards",
    AgentCard,
    ("name",),
    frozenset({
        "prompts", "tools", "limits", "grading", "failsafes", "foundation_pieces",
    }),
)
_AGENT_RUNS = _Spec("agent_runs", AgentRun, ("id",))
_BUDGET_SLICES = _Spec("budget_slices", BudgetSlice, ("scope",))
_GRADE_RECORDS = _Spec(
    "grade_records",
    GradeRecord,
    ("id",),
    frozenset({"criteria", "feedback_for_generator"}),
)
_GRADER_HEALTH = _Spec(
    "grader_health", GraderHealth, (), frozenset({"top_rejection_reasons"})
)
_PROPOSALS = _Spec(
    "proposals",
    Proposal,
    ("id",),
    frozenset(
        {
            "what_was_found",
            "connects_to_units",
            "message_ids",
            "media_work",
            "placements",
            "modes",
            "questions",
            "risks",
        }
    ),
)
_PROPOSAL_DECISIONS = _Spec(
    "proposal_decisions", ProposalDecision, ("proposal_id",), frozenset({"answers"})
)
_PLAN_ITEMS = _Spec(
    "integration_plan_items",
    IntegrationPlanItem,
    ("id",),
    frozenset({"placement", "mode", "author_answers", "evidence_ids"}),
)
_REVISION_HUNKS = _Spec(
    "revision_hunks",
    RevisionHunk,
    ("id",),
    frozenset({"unit_ids", "before_span", "evidence_ids", "legal_issue_ids"}),
)
_REVISIONS = _Spec("revisions", Revision, ("id",), frozenset({"hunks"}))
_STYLE_GUIDES = _Spec(
    "style_guides",
    StyleGuide,
    ("version",),
    frozenset(
        {
            "dos",
            "donts",
            "protected_terms",
            "intentional_patterns",
            "punctuation_habits",
            "rhythm_targets",
            "examples",
        }
    ),
)
_STYLE_REPORTS = _Spec(
    "style_reports",
    StyleReport,
    ("id",),
    frozenset(
        {
            "fingerprint_before",
            "fingerprint_after",
            "per_hunk_similarity",
            "drift_notes",
            "tone_shift",
            "fix_requests",
        }
    ),
)
_CROSS_CHECK_REPORTS = _Spec(
    "cross_check_reports", CrossCheckReport, ("id",), frozenset({"items", "notes"})
)
_PERSONAS = _Spec("personas", Persona, ("id",), frozenset({"values"}))
_MECHANICS_FINDINGS = _Spec(
    "mechanics_findings", MechanicsFinding, ("id",), frozenset({"unit_ids"})
)
_PERSONA_REACTIONS = _Spec(
    "persona_reactions",
    PersonaReaction,
    ("id",),
    frozenset({"felt", "confusing_parts", "cringe_parts", "strongest_line", "disagreements"}),
)
_SCORECARDS = _Spec(
    "audience_scorecards",
    AudienceScorecard,
    ("id",),
    frozenset(
        {
            "metric_means",
            "cohort_means",
            "metric_sd",
            "metric_min",
            "metric_max",
            "journey_curve",
            "hotspots",
            "strong_lines",
        }
    ),
)
_AUDIENCE_BRIEFS = _Spec(
    "audience_briefs",
    AudienceBrief,
    ("id",),
    frozenset({"priorities", "do_not_touch", "voice_cautions"}),
)
_CALIBRATION = _Spec("calibration", CalibrationRecord, ("id",))
_PLAYBOOK = _Spec("playbook", PlaybookEntry, ("technique", "cohort", "metric"))
_LEGAL_ISSUES = _Spec(
    "legal_issues",
    LegalIssue,
    ("id",),
    frozenset({"unit_ids", "issue_types", "persons_involved", "assigned_counsel"}),
)
_POSITIONS = _Spec(
    "positions",
    Position,
    ("id",),
    frozenset({"authorities", "proposed_edits", "rebuttals"}),
)
_DEFENSE_MEMOS = _Spec(
    "defense_memos",
    DefenseMemo,
    ("id",),
    frozenset({"defense_basis", "required_edits", "answered_dissents", "endorsements"}),
)
_LEARNING_CHANGES = _Spec("learning_changes", LearningChange, ("id",))
_PROMPT_TRIALS = _Spec(
    "prompt_trials",
    PromptTrial,
    ("id",),
    frozenset({"metric_deltas", "release_blocker_regressions"}),
)

_SPECS: tuple[_Spec, ...] = (
    _DOCUMENTS, _CHUNKS, _UNITS, _EVIDENCE, _FETCHED_DOCS, _SEARCH_HITS,
    _VERDICTS, _DISCOVERY_NOTES, _SPECIALIST_FINDINGS, _MEDIA_WORKS, _MEDIA_CHECKS,
    _ENGINE_FINDINGS, _SYNTHESES, _CORE_MESSAGES, _MESSAGE_MAPPINGS, _DRIFT_REPORTS,
    _VOICE_FINGERPRINTS, _VOICE_COMPARISONS, _SHADOW_REPORTS, _AUTHOR_PROFILES,
    _BOOK_PROFILES, _CHAPTER_BRIEFS, _RUNS, _LLM_CALLS, _CACHE, _CHAPTER_STATE, _CONCEPTS,
    _CONCEPT_EDGES, _CONCEPT_GRAPHS, _EXPANSION_THREADS, _RESEARCH_BRIEFS,
    _RESEARCH_NOTES, _DEEP_REPORTS, _MARGIN_NOTES, _INTEGRATION_BRIEFS, _CRITIC_SCORES,
    _AGENT_CARDS, _AGENT_RUNS, _BUDGET_SLICES, _GRADE_RECORDS, _GRADER_HEALTH,
    _PROPOSALS, _PROPOSAL_DECISIONS, _PLAN_ITEMS, _REVISION_HUNKS, _REVISIONS,
    _STYLE_GUIDES, _STYLE_REPORTS, _CROSS_CHECK_REPORTS, _PERSONAS, _MECHANICS_FINDINGS,
    _PERSONA_REACTIONS, _SCORECARDS, _AUDIENCE_BRIEFS, _CALIBRATION, _PLAYBOOK,
    _LEGAL_ISSUES, _POSITIONS, _DEFENSE_MEMOS, _LEARNING_CHANGES, _PROMPT_TRIALS,
)

_BY_MODEL: dict[type[BaseModel], _Spec] = {s.model: s for s in _SPECS}
