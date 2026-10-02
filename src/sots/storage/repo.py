"""Typed persistence for every SotS model (P01 T01.032/T01.033/T01.035).

This is the **only** module that runs SQL (plus `db.py` for pragmas and
migrations; enforced by `tests/unit/test_architecture.py`).

Conventions: scalar fields map to TEXT/INTEGER/REAL columns, list/dict/nested
fields to JSON TEXT columns (`to_json`/`from_json`). Datetimes, dates, and
enums are stored as ISO TEXT and re-validated by pydantic on load. `save_*`
is an upsert on the primary key; `get_*` returns `None` when missing;
`list_*` filters are `column=value` conjunctions (`None` means "no filter").
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

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


def to_json(value: Any) -> str:
    """Serialize a list/dict/nested value for a JSON TEXT column."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def from_json(text: str) -> Any:
    """Parse a JSON TEXT column back to Python data."""
    return json.loads(text)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass(frozen=True)
class _Spec:
    table: str
    model: type[BaseModel]
    pk: tuple[str, ...]  # model fields forming the PK; () = surrogate AUTOINCREMENT id
    json_fields: frozenset[str] = frozenset()

    @property
    def columns(self) -> list[str]:
        cols = list(self.model.model_fields)
        if not self.pk:
            cols = ["id", *cols]
        return cols


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


def _dump_row(spec: _Spec, model: BaseModel) -> dict[str, Any]:
    dumped = model.model_dump(mode="json")
    row: dict[str, Any] = {}
    for fname in spec.model.model_fields:
        value = dumped[fname]
        if fname in spec.json_fields and value is not None:
            value = to_json(value)
        row[fname] = value
    return row


def _load_row(spec: _Spec, row: Any) -> BaseModel:
    data = dict(row)
    fields = spec.model.model_fields
    kwargs: dict[str, Any] = {}
    for fname in fields:
        value = data.get(fname)
        if fname in spec.json_fields and value is not None:
            value = from_json(value)
        kwargs[fname] = value
    return spec.model(**kwargs)


def _save(conn: sqlite3.Connection, spec: _Spec, model: BaseModel) -> Any:
    row = _dump_row(spec, model)
    cols = list(row)
    placeholders = ", ".join("?" for _ in cols)
    sql = (
        f"INSERT OR REPLACE INTO {_q(spec.table)}"
        f" ({', '.join(_q(c) for c in cols)}) VALUES ({placeholders})"
    )
    with conn:
        cur = conn.execute(sql, [row[c] for c in cols])
    if spec.pk:
        keys = tuple(getattr(model, k) for k in spec.pk)
        return keys[0] if len(keys) == 1 else keys
    return cur.lastrowid


def _get(conn: sqlite3.Connection, spec: _Spec, key: Any) -> BaseModel | None:
    if not spec.pk:
        sql = f"SELECT * FROM {_q(spec.table)} WHERE {_q('id')} = ?"
        params: tuple[Any, ...] = (key,)
    else:
        keys = key if isinstance(key, tuple) else (key,)
        where = " AND ".join(f"{_q(c)} = ?" for c in spec.pk)
        sql = f"SELECT * FROM {_q(spec.table)} WHERE {where}"
        params = keys
    row = conn.execute(sql, params).fetchone()
    return _load_row(spec, row) if row is not None else None


def _list(
    conn: sqlite3.Connection, spec: _Spec, *, limit: int | None = None, **filters: Any
) -> list[BaseModel]:
    known = set(spec.columns)
    clauses: list[str] = []
    params: list[Any] = []
    for name, value in filters.items():
        if name not in known:
            raise ValueError(f"unknown filter {name!r} for table {spec.table}")
        if value is None:
            continue
        clauses.append(f"{_q(name)} = ?")
        params.append(value)
    sql = f"SELECT * FROM {_q(spec.table)}"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return [_load_row(spec, row) for row in conn.execute(sql, params)]


def _delete(conn: sqlite3.Connection, spec: _Spec, key: Any) -> bool:
    if not spec.pk:
        sql = f"DELETE FROM {_q(spec.table)} WHERE {_q('id')} = ?"
        params: tuple[Any, ...] = (key,)
    else:
        keys = key if isinstance(key, tuple) else (key,)
        where = " AND ".join(f"{_q(c)} = ?" for c in spec.pk)
        sql = f"DELETE FROM {_q(spec.table)} WHERE {where}"
        params = keys
    with conn:
        cur = conn.execute(sql, params)
    return cur.rowcount > 0


# --- documents / chunks / units ------------------------------------------------

def save_document(conn: sqlite3.Connection, doc: Document) -> str:
    return cast(str, _save(conn, _DOCUMENTS, doc))


def get_document(conn: sqlite3.Connection, doc_id: str) -> Document | None:
    return cast(Document | None, _get(conn, _DOCUMENTS, doc_id))


def list_documents(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Document]:
    return cast(list[Document], _list(conn, _DOCUMENTS, limit=limit, **filters))


def save_chunk(conn: sqlite3.Connection, chunk: Chunk) -> str:
    return cast(str, _save(conn, _CHUNKS, chunk))


def get_chunk(conn: sqlite3.Connection, chunk_id: str) -> Chunk | None:
    return cast(Chunk | None, _get(conn, _CHUNKS, chunk_id))


def list_chunks(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Chunk]:
    return cast(list[Chunk], _list(conn, _CHUNKS, limit=limit, **filters))


def save_unit(conn: sqlite3.Connection, unit: Unit) -> str:
    return cast(str, _save(conn, _UNITS, unit))


def get_unit(conn: sqlite3.Connection, unit_id: str) -> Unit | None:
    return cast(Unit | None, _get(conn, _UNITS, unit_id))


def list_units(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Unit]:
    return cast(list[Unit], _list(conn, _UNITS, limit=limit, **filters))


# --- evidence / verdicts -------------------------------------------------------

def save_evidence(conn: sqlite3.Connection, evidence: Evidence) -> str:
    return cast(str, _save(conn, _EVIDENCE, evidence))


def get_evidence(conn: sqlite3.Connection, evidence_id: str) -> Evidence | None:
    return cast(Evidence | None, _get(conn, _EVIDENCE, evidence_id))


def list_evidence(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Evidence]:
    return cast(list[Evidence], _list(conn, _EVIDENCE, limit=limit, **filters))


def save_fetched_doc(conn: sqlite3.Connection, doc: FetchedDoc) -> str:
    return cast(str, _save(conn, _FETCHED_DOCS, doc))


def get_fetched_doc(conn: sqlite3.Connection, url: str) -> FetchedDoc | None:
    return cast(FetchedDoc | None, _get(conn, _FETCHED_DOCS, url))


def list_fetched_docs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[FetchedDoc]:
    return cast(list[FetchedDoc], _list(conn, _FETCHED_DOCS, limit=limit, **filters))


def save_supplement_doc(conn: sqlite3.Connection, doc: SupplementDoc) -> str:
    return cast(str, _save(conn, _SUPPLEMENT_DOCS, doc))


def get_supplement_doc(conn: sqlite3.Connection, path: str) -> SupplementDoc | None:
    return cast(SupplementDoc | None, _get(conn, _SUPPLEMENT_DOCS, path))


def list_supplement_docs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SupplementDoc]:
    return cast(
        list[SupplementDoc], _list(conn, _SUPPLEMENT_DOCS, limit=limit, **filters)
    )


def save_search_hit(conn: sqlite3.Connection, hit: SearchHit) -> int:
    return cast(int, _save(conn, _SEARCH_HITS, hit))


def get_search_hit(conn: sqlite3.Connection, hit_id: int) -> SearchHit | None:
    return cast(SearchHit | None, _get(conn, _SEARCH_HITS, hit_id))


def list_search_hits(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SearchHit]:
    return cast(list[SearchHit], _list(conn, _SEARCH_HITS, limit=limit, **filters))


def save_verdict(conn: sqlite3.Connection, record: VerdictRecord) -> str:
    return cast(str, _save(conn, _VERDICTS, record))


def get_verdict(conn: sqlite3.Connection, verdict_id: str) -> VerdictRecord | None:
    return cast(VerdictRecord | None, _get(conn, _VERDICTS, verdict_id))


def list_verdicts(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VerdictRecord]:
    return cast(list[VerdictRecord], _list(conn, _VERDICTS, limit=limit, **filters))


def save_discovery_note(conn: sqlite3.Connection, note: DiscoveryNote) -> str:
    return cast(str, _save(conn, _DISCOVERY_NOTES, note))


def get_discovery_note(conn: sqlite3.Connection, note_id: str) -> DiscoveryNote | None:
    return cast(DiscoveryNote | None, _get(conn, _DISCOVERY_NOTES, note_id))


def list_discovery_notes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DiscoveryNote]:
    return cast(list[DiscoveryNote], _list(conn, _DISCOVERY_NOTES, limit=limit, **filters))


def save_specialist_findings(
    conn: sqlite3.Connection, findings: SpecialistFindings
) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _SPECIALIST_FINDINGS, findings))


def get_specialist_findings(
    conn: sqlite3.Connection, unit_id: str, specialist: str
) -> SpecialistFindings | None:
    return cast(
        SpecialistFindings | None, _get(conn, _SPECIALIST_FINDINGS, (unit_id, specialist))
    )


def list_specialist_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[SpecialistFindings]:
    return cast(
        list[SpecialistFindings], _list(conn, _SPECIALIST_FINDINGS, limit=limit, **filters)
    )


# --- media / psyche ------------------------------------------------------------

def save_media_work(conn: sqlite3.Connection, work: MediaWork) -> str:
    return cast(str, _save(conn, _MEDIA_WORKS, work))


def get_media_work(conn: sqlite3.Connection, work_id: str) -> MediaWork | None:
    return cast(MediaWork | None, _get(conn, _MEDIA_WORKS, work_id))


def list_media_works(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MediaWork]:
    return cast(list[MediaWork], _list(conn, _MEDIA_WORKS, limit=limit, **filters))


def save_media_check(conn: sqlite3.Connection, check: MediaCheck) -> str:
    return cast(str, _save(conn, _MEDIA_CHECKS, check))


def get_media_check(conn: sqlite3.Connection, check_id: str) -> MediaCheck | None:
    return cast(MediaCheck | None, _get(conn, _MEDIA_CHECKS, check_id))


def list_media_checks(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MediaCheck]:
    return cast(list[MediaCheck], _list(conn, _MEDIA_CHECKS, limit=limit, **filters))


def save_engine_finding(conn: sqlite3.Connection, finding: EngineFinding) -> str:
    return cast(str, _save(conn, _ENGINE_FINDINGS, finding))


def get_engine_finding(conn: sqlite3.Connection, finding_id: str) -> EngineFinding | None:
    return cast(EngineFinding | None, _get(conn, _ENGINE_FINDINGS, finding_id))


def list_engine_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[EngineFinding]:
    return cast(
        list[EngineFinding], _list(conn, _ENGINE_FINDINGS, limit=limit, **filters)
    )


def save_synthesis(conn: sqlite3.Connection, synthesis: Synthesis) -> str:
    return cast(str, _save(conn, _SYNTHESES, synthesis))


def get_synthesis(conn: sqlite3.Connection, run_id: str) -> Synthesis | None:
    return cast(Synthesis | None, _get(conn, _SYNTHESES, run_id))


def list_syntheses(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Synthesis]:
    return cast(list[Synthesis], _list(conn, _SYNTHESES, limit=limit, **filters))


# --- narrative / voice / shadow ------------------------------------------------

def save_core_message(conn: sqlite3.Connection, message: CoreMessage) -> str:
    return cast(str, _save(conn, _CORE_MESSAGES, message))


def get_core_message(conn: sqlite3.Connection, message_id: str) -> CoreMessage | None:
    return cast(CoreMessage | None, _get(conn, _CORE_MESSAGES, message_id))


def list_core_messages(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CoreMessage]:
    return cast(list[CoreMessage], _list(conn, _CORE_MESSAGES, limit=limit, **filters))


def save_message_mapping(conn: sqlite3.Connection, mapping: MessageMapping) -> str:
    return cast(str, _save(conn, _MESSAGE_MAPPINGS, mapping))


def get_message_mapping(conn: sqlite3.Connection, unit_id: str) -> MessageMapping | None:
    return cast(MessageMapping | None, _get(conn, _MESSAGE_MAPPINGS, unit_id))


def list_message_mappings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MessageMapping]:
    return cast(
        list[MessageMapping], _list(conn, _MESSAGE_MAPPINGS, limit=limit, **filters)
    )


def save_drift_report(conn: sqlite3.Connection, report: DriftReport) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _DRIFT_REPORTS, report))


def get_drift_report(
    conn: sqlite3.Connection, run_id: str, document_id: str
) -> DriftReport | None:
    return cast(
        DriftReport | None, _get(conn, _DRIFT_REPORTS, (run_id, document_id))
    )


def list_drift_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DriftReport]:
    return cast(list[DriftReport], _list(conn, _DRIFT_REPORTS, limit=limit, **filters))


def save_voice_fingerprint(conn: sqlite3.Connection, fingerprint: VoiceFingerprint) -> int:
    return cast(int, _save(conn, _VOICE_FINGERPRINTS, fingerprint))


def get_voice_fingerprint(
    conn: sqlite3.Connection, fingerprint_id: int
) -> VoiceFingerprint | None:
    return cast(VoiceFingerprint | None, _get(conn, _VOICE_FINGERPRINTS, fingerprint_id))


def list_voice_fingerprints(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VoiceFingerprint]:
    return cast(
        list[VoiceFingerprint], _list(conn, _VOICE_FINGERPRINTS, limit=limit, **filters)
    )


def save_voice_comparison(conn: sqlite3.Connection, comparison: VoiceComparison) -> tuple[str, str]:
    return cast(tuple[str, str], _save(conn, _VOICE_COMPARISONS, comparison))


def get_voice_comparison(
    conn: sqlite3.Connection, run_id: str, document_id: str
) -> VoiceComparison | None:
    return cast(
        VoiceComparison | None, _get(conn, _VOICE_COMPARISONS, (run_id, document_id))
    )


def list_voice_comparisons(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[VoiceComparison]:
    return cast(
        list[VoiceComparison], _list(conn, _VOICE_COMPARISONS, limit=limit, **filters)
    )


def save_shadow_report(conn: sqlite3.Connection, report: ShadowReport) -> str:
    return cast(str, _save(conn, _SHADOW_REPORTS, report))


def get_shadow_report(conn: sqlite3.Connection, report_id: str) -> ShadowReport | None:
    return cast(ShadowReport | None, _get(conn, _SHADOW_REPORTS, report_id))


def list_shadow_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ShadowReport]:
    return cast(list[ShadowReport], _list(conn, _SHADOW_REPORTS, limit=limit, **filters))


# --- profile / runs ------------------------------------------------------------

def save_author_profile(conn: sqlite3.Connection, profile: AuthorProfile) -> int:
    return cast(int, _save(conn, _AUTHOR_PROFILES, profile))


def get_author_profile(conn: sqlite3.Connection, profile_id: int) -> AuthorProfile | None:
    return cast(AuthorProfile | None, _get(conn, _AUTHOR_PROFILES, profile_id))


def list_author_profiles(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AuthorProfile]:
    return cast(
        list[AuthorProfile], _list(conn, _AUTHOR_PROFILES, limit=limit, **filters)
    )


def save_book_profile(conn: sqlite3.Connection, profile: BookProfile) -> int:
    return cast(int, _save(conn, _BOOK_PROFILES, profile))


def get_book_profile(conn: sqlite3.Connection, profile_id: int) -> BookProfile | None:
    return cast(BookProfile | None, _get(conn, _BOOK_PROFILES, profile_id))


def list_book_profiles(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[BookProfile]:
    return cast(list[BookProfile], _list(conn, _BOOK_PROFILES, limit=limit, **filters))


def save_chapter_brief(conn: sqlite3.Connection, brief: ChapterBrief) -> str:
    return cast(str, _save(conn, _CHAPTER_BRIEFS, brief))


def get_chapter_brief(conn: sqlite3.Connection, chapter_id: str) -> ChapterBrief | None:
    return cast(ChapterBrief | None, _get(conn, _CHAPTER_BRIEFS, chapter_id))


def list_chapter_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ChapterBrief]:
    return cast(
        list[ChapterBrief], _list(conn, _CHAPTER_BRIEFS, limit=limit, **filters)
    )


def save_run(conn: sqlite3.Connection, run: Run) -> str:
    return cast(str, _save(conn, _RUNS, run))


def get_run(conn: sqlite3.Connection, run_id: str) -> Run | None:
    return cast(Run | None, _get(conn, _RUNS, run_id))


def list_runs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Run]:
    return cast(list[Run], _list(conn, _RUNS, limit=limit, **filters))


def save_llm_call(conn: sqlite3.Connection, call: LLMCall) -> str:
    return cast(str, _save(conn, _LLM_CALLS, call))


def get_llm_call(conn: sqlite3.Connection, call_id: str) -> LLMCall | None:
    return cast(LLMCall | None, _get(conn, _LLM_CALLS, call_id))


def list_llm_calls(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LLMCall]:
    return cast(list[LLMCall], _list(conn, _LLM_CALLS, limit=limit, **filters))


def save_cache_entry(conn: sqlite3.Connection, entry: CacheEntry) -> str:
    return cast(str, _save(conn, _CACHE, entry))


def get_cache_entry(conn: sqlite3.Connection, key: str) -> CacheEntry | None:
    return cast(CacheEntry | None, _get(conn, _CACHE, key))


def count_cache_entries(conn: sqlite3.Connection) -> int:
    row = conn.execute('SELECT COUNT(*) AS n FROM "cache"').fetchone()
    return int(row["n"])


def save_chapter_state(conn: sqlite3.Connection, state: ChapterState) -> str:
    return cast(str, _save(conn, _CHAPTER_STATE, state))


def get_chapter_state(conn: sqlite3.Connection, chapter_id: str) -> ChapterState | None:
    return cast(ChapterState | None, _get(conn, _CHAPTER_STATE, chapter_id))


def list_chapter_states(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ChapterState]:
    return cast(
        list[ChapterState], _list(conn, _CHAPTER_STATE, limit=limit, **filters)
    )


# --- expansion -----------------------------------------------------------------

def save_concept(conn: sqlite3.Connection, concept: Concept) -> str:
    return cast(str, _save(conn, _CONCEPTS, concept))


def get_concept(conn: sqlite3.Connection, concept_id: str) -> Concept | None:
    return cast(Concept | None, _get(conn, _CONCEPTS, concept_id))


def list_concepts(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Concept]:
    return cast(list[Concept], _list(conn, _CONCEPTS, limit=limit, **filters))


def save_concept_edge(conn: sqlite3.Connection, edge: ConceptEdge) -> tuple[str, str, str]:
    return cast(tuple[str, str, str], _save(conn, _CONCEPT_EDGES, edge))


def get_concept_edge(
    conn: sqlite3.Connection, source_id: str, target_id: str, relation: str
) -> ConceptEdge | None:
    return cast(
        ConceptEdge | None, _get(conn, _CONCEPT_EDGES, (source_id, target_id, relation))
    )


def list_concept_edges(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ConceptEdge]:
    return cast(list[ConceptEdge], _list(conn, _CONCEPT_EDGES, limit=limit, **filters))


def save_concept_graph(conn: sqlite3.Connection, graph: ConceptGraph) -> str:
    return cast(str, _save(conn, _CONCEPT_GRAPHS, graph))


def get_concept_graph(conn: sqlite3.Connection, run_id: str) -> ConceptGraph | None:
    return cast(ConceptGraph | None, _get(conn, _CONCEPT_GRAPHS, run_id))


def list_concept_graphs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ConceptGraph]:
    return cast(
        list[ConceptGraph], _list(conn, _CONCEPT_GRAPHS, limit=limit, **filters)
    )


def save_expansion_thread(conn: sqlite3.Connection, thread: ExpansionThread) -> str:
    return cast(str, _save(conn, _EXPANSION_THREADS, thread))


def get_expansion_thread(conn: sqlite3.Connection, thread_id: str) -> ExpansionThread | None:
    return cast(ExpansionThread | None, _get(conn, _EXPANSION_THREADS, thread_id))


def list_expansion_threads(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ExpansionThread]:
    return cast(
        list[ExpansionThread], _list(conn, _EXPANSION_THREADS, limit=limit, **filters)
    )


def save_research_brief(conn: sqlite3.Connection, brief: ResearchBrief) -> str:
    return cast(str, _save(conn, _RESEARCH_BRIEFS, brief))


def get_research_brief(conn: sqlite3.Connection, thread_id: str) -> ResearchBrief | None:
    return cast(ResearchBrief | None, _get(conn, _RESEARCH_BRIEFS, thread_id))


def list_research_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ResearchBrief]:
    return cast(
        list[ResearchBrief], _list(conn, _RESEARCH_BRIEFS, limit=limit, **filters)
    )


def save_research_note(conn: sqlite3.Connection, note: ResearchNote) -> str:
    return cast(str, _save(conn, _RESEARCH_NOTES, note))


def get_research_note(conn: sqlite3.Connection, note_id: str) -> ResearchNote | None:
    return cast(ResearchNote | None, _get(conn, _RESEARCH_NOTES, note_id))


def list_research_notes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ResearchNote]:
    return cast(
        list[ResearchNote], _list(conn, _RESEARCH_NOTES, limit=limit, **filters)
    )


def save_deep_research_report(
    conn: sqlite3.Connection, report: DeepResearchReport
) -> str:
    return cast(str, _save(conn, _DEEP_REPORTS, report))


def get_deep_research_report(
    conn: sqlite3.Connection, report_id: str
) -> DeepResearchReport | None:
    return cast(DeepResearchReport | None, _get(conn, _DEEP_REPORTS, report_id))


def list_deep_research_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DeepResearchReport]:
    return cast(
        list[DeepResearchReport], _list(conn, _DEEP_REPORTS, limit=limit, **filters)
    )


def save_margin_note(conn: sqlite3.Connection, note: MarginNote) -> str:
    return cast(str, _save(conn, _MARGIN_NOTES, note))


def get_margin_note(conn: sqlite3.Connection, note_id: str) -> MarginNote | None:
    return cast(MarginNote | None, _get(conn, _MARGIN_NOTES, note_id))


def list_margin_notes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MarginNote]:
    return cast(list[MarginNote], _list(conn, _MARGIN_NOTES, limit=limit, **filters))


def save_integration_brief(conn: sqlite3.Connection, brief: IntegrationBrief) -> str:
    return cast(str, _save(conn, _INTEGRATION_BRIEFS, brief))


def get_integration_brief(conn: sqlite3.Connection, brief_id: str) -> IntegrationBrief | None:
    return cast(IntegrationBrief | None, _get(conn, _INTEGRATION_BRIEFS, brief_id))


def list_integration_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[IntegrationBrief]:
    return cast(
        list[IntegrationBrief], _list(conn, _INTEGRATION_BRIEFS, limit=limit, **filters)
    )


def save_critic_score(conn: sqlite3.Connection, score: CriticScore) -> str:
    return cast(str, _save(conn, _CRITIC_SCORES, score))


def get_critic_score(conn: sqlite3.Connection, target_id: str) -> CriticScore | None:
    return cast(CriticScore | None, _get(conn, _CRITIC_SCORES, target_id))


def list_critic_scores(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CriticScore]:
    return cast(list[CriticScore], _list(conn, _CRITIC_SCORES, limit=limit, **filters))


# --- agents / grading ----------------------------------------------------------

def save_agent_card(conn: sqlite3.Connection, card: AgentCard) -> str:
    return cast(str, _save(conn, _AGENT_CARDS, card))


def get_agent_card(conn: sqlite3.Connection, name: str) -> AgentCard | None:
    return cast(AgentCard | None, _get(conn, _AGENT_CARDS, name))


def list_agent_cards(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AgentCard]:
    return cast(list[AgentCard], _list(conn, _AGENT_CARDS, limit=limit, **filters))


def save_agent_run(conn: sqlite3.Connection, run: AgentRun) -> str:
    return cast(str, _save(conn, _AGENT_RUNS, run))


def get_agent_run(conn: sqlite3.Connection, run_id: str) -> AgentRun | None:
    return cast(AgentRun | None, _get(conn, _AGENT_RUNS, run_id))


def list_agent_runs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AgentRun]:
    return cast(list[AgentRun], _list(conn, _AGENT_RUNS, limit=limit, **filters))


def save_budget_slice(conn: sqlite3.Connection, budget_slice: BudgetSlice) -> str:
    return cast(str, _save(conn, _BUDGET_SLICES, budget_slice))


def get_budget_slice(conn: sqlite3.Connection, scope: str) -> BudgetSlice | None:
    return cast(BudgetSlice | None, _get(conn, _BUDGET_SLICES, scope))


def list_budget_slices(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[BudgetSlice]:
    return cast(list[BudgetSlice], _list(conn, _BUDGET_SLICES, limit=limit, **filters))


def save_grade_record(conn: sqlite3.Connection, record: GradeRecord) -> str:
    return cast(str, _save(conn, _GRADE_RECORDS, record))


def get_grade_record(conn: sqlite3.Connection, record_id: str) -> GradeRecord | None:
    return cast(GradeRecord | None, _get(conn, _GRADE_RECORDS, record_id))


def list_grade_records(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[GradeRecord]:
    return cast(list[GradeRecord], _list(conn, _GRADE_RECORDS, limit=limit, **filters))


def save_grader_health(conn: sqlite3.Connection, health: GraderHealth) -> int:
    return cast(int, _save(conn, _GRADER_HEALTH, health))


def get_grader_health(conn: sqlite3.Connection, health_id: int) -> GraderHealth | None:
    return cast(GraderHealth | None, _get(conn, _GRADER_HEALTH, health_id))


def list_grader_health(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[GraderHealth]:
    return cast(list[GraderHealth], _list(conn, _GRADER_HEALTH, limit=limit, **filters))


# --- proposals / rewrite -------------------------------------------------------

def save_proposal(conn: sqlite3.Connection, proposal: Proposal) -> str:
    return cast(str, _save(conn, _PROPOSALS, proposal))


def get_proposal(conn: sqlite3.Connection, proposal_id: str) -> Proposal | None:
    return cast(Proposal | None, _get(conn, _PROPOSALS, proposal_id))


def list_proposals(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Proposal]:
    return cast(list[Proposal], _list(conn, _PROPOSALS, limit=limit, **filters))


def save_proposal_decision(conn: sqlite3.Connection, decision: ProposalDecision) -> str:
    return cast(str, _save(conn, _PROPOSAL_DECISIONS, decision))


def get_proposal_decision(
    conn: sqlite3.Connection, proposal_id: str
) -> ProposalDecision | None:
    return cast(ProposalDecision | None, _get(conn, _PROPOSAL_DECISIONS, proposal_id))


def list_proposal_decisions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[ProposalDecision]:
    return cast(
        list[ProposalDecision], _list(conn, _PROPOSAL_DECISIONS, limit=limit, **filters)
    )


def save_integration_plan_item(
    conn: sqlite3.Connection, item: IntegrationPlanItem
) -> str:
    return cast(str, _save(conn, _PLAN_ITEMS, item))


def get_integration_plan_item(
    conn: sqlite3.Connection, item_id: str
) -> IntegrationPlanItem | None:
    return cast(IntegrationPlanItem | None, _get(conn, _PLAN_ITEMS, item_id))


def list_integration_plan_items(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[IntegrationPlanItem]:
    return cast(
        list[IntegrationPlanItem], _list(conn, _PLAN_ITEMS, limit=limit, **filters)
    )


def save_revision_hunk(conn: sqlite3.Connection, hunk: RevisionHunk) -> str:
    return cast(str, _save(conn, _REVISION_HUNKS, hunk))


def get_revision_hunk(conn: sqlite3.Connection, hunk_id: str) -> RevisionHunk | None:
    return cast(RevisionHunk | None, _get(conn, _REVISION_HUNKS, hunk_id))


def list_revision_hunks(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[RevisionHunk]:
    return cast(
        list[RevisionHunk], _list(conn, _REVISION_HUNKS, limit=limit, **filters)
    )


def save_revision(conn: sqlite3.Connection, revision: Revision) -> str:
    return cast(str, _save(conn, _REVISIONS, revision))


def get_revision(conn: sqlite3.Connection, revision_id: str) -> Revision | None:
    return cast(Revision | None, _get(conn, _REVISIONS, revision_id))


def list_revisions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Revision]:
    return cast(list[Revision], _list(conn, _REVISIONS, limit=limit, **filters))


def save_style_guide(conn: sqlite3.Connection, guide: StyleGuide) -> int:
    return cast(int, _save(conn, _STYLE_GUIDES, guide))


def get_style_guide(conn: sqlite3.Connection, version: int) -> StyleGuide | None:
    return cast(StyleGuide | None, _get(conn, _STYLE_GUIDES, version))


def list_style_guides(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[StyleGuide]:
    return cast(list[StyleGuide], _list(conn, _STYLE_GUIDES, limit=limit, **filters))


def save_style_report(conn: sqlite3.Connection, report: StyleReport) -> str:
    return cast(str, _save(conn, _STYLE_REPORTS, report))


def get_style_report(conn: sqlite3.Connection, report_id: str) -> StyleReport | None:
    return cast(StyleReport | None, _get(conn, _STYLE_REPORTS, report_id))


def list_style_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[StyleReport]:
    return cast(list[StyleReport], _list(conn, _STYLE_REPORTS, limit=limit, **filters))


def save_cross_check_report(conn: sqlite3.Connection, report: CrossCheckReport) -> str:
    return cast(str, _save(conn, _CROSS_CHECK_REPORTS, report))


def get_cross_check_report(
    conn: sqlite3.Connection, report_id: str
) -> CrossCheckReport | None:
    return cast(CrossCheckReport | None, _get(conn, _CROSS_CHECK_REPORTS, report_id))


def list_cross_check_reports(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CrossCheckReport]:
    return cast(
        list[CrossCheckReport], _list(conn, _CROSS_CHECK_REPORTS, limit=limit, **filters)
    )


# --- audience ------------------------------------------------------------------

def save_persona(conn: sqlite3.Connection, persona: Persona) -> str:
    return cast(str, _save(conn, _PERSONAS, persona))


def get_persona(conn: sqlite3.Connection, persona_id: str) -> Persona | None:
    return cast(Persona | None, _get(conn, _PERSONAS, persona_id))


def list_personas(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Persona]:
    return cast(list[Persona], _list(conn, _PERSONAS, limit=limit, **filters))


def save_mechanics_finding(
    conn: sqlite3.Connection, finding: MechanicsFinding
) -> str:
    return cast(str, _save(conn, _MECHANICS_FINDINGS, finding))


def get_mechanics_finding(
    conn: sqlite3.Connection, finding_id: str
) -> MechanicsFinding | None:
    return cast(MechanicsFinding | None, _get(conn, _MECHANICS_FINDINGS, finding_id))


def list_mechanics_findings(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[MechanicsFinding]:
    return cast(
        list[MechanicsFinding], _list(conn, _MECHANICS_FINDINGS, limit=limit, **filters)
    )


def save_persona_reaction(conn: sqlite3.Connection, reaction: PersonaReaction) -> str:
    return cast(str, _save(conn, _PERSONA_REACTIONS, reaction))


def get_persona_reaction(
    conn: sqlite3.Connection, reaction_id: str
) -> PersonaReaction | None:
    return cast(PersonaReaction | None, _get(conn, _PERSONA_REACTIONS, reaction_id))


def list_persona_reactions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PersonaReaction]:
    return cast(
        list[PersonaReaction], _list(conn, _PERSONA_REACTIONS, limit=limit, **filters)
    )


def save_audience_scorecard(
    conn: sqlite3.Connection, scorecard: AudienceScorecard
) -> str:
    return cast(str, _save(conn, _SCORECARDS, scorecard))


def get_audience_scorecard(
    conn: sqlite3.Connection, scorecard_id: str
) -> AudienceScorecard | None:
    return cast(AudienceScorecard | None, _get(conn, _SCORECARDS, scorecard_id))


def list_audience_scorecards(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AudienceScorecard]:
    return cast(
        list[AudienceScorecard], _list(conn, _SCORECARDS, limit=limit, **filters)
    )


def save_audience_brief(conn: sqlite3.Connection, brief: AudienceBrief) -> str:
    return cast(str, _save(conn, _AUDIENCE_BRIEFS, brief))


def get_audience_brief(conn: sqlite3.Connection, brief_id: str) -> AudienceBrief | None:
    return cast(AudienceBrief | None, _get(conn, _AUDIENCE_BRIEFS, brief_id))


def list_audience_briefs(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[AudienceBrief]:
    return cast(
        list[AudienceBrief], _list(conn, _AUDIENCE_BRIEFS, limit=limit, **filters)
    )


def save_calibration_record(conn: sqlite3.Connection, record: CalibrationRecord) -> str:
    return cast(str, _save(conn, _CALIBRATION, record))


def get_calibration_record(
    conn: sqlite3.Connection, record_id: str
) -> CalibrationRecord | None:
    return cast(CalibrationRecord | None, _get(conn, _CALIBRATION, record_id))


def list_calibration_records(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[CalibrationRecord]:
    return cast(
        list[CalibrationRecord], _list(conn, _CALIBRATION, limit=limit, **filters)
    )


def save_playbook_entry(
    conn: sqlite3.Connection, entry: PlaybookEntry
) -> tuple[str, str, str]:
    return cast(tuple[str, str, str], _save(conn, _PLAYBOOK, entry))


def get_playbook_entry(
    conn: sqlite3.Connection, technique: str, cohort: str, metric: str
) -> PlaybookEntry | None:
    return cast(
        PlaybookEntry | None, _get(conn, _PLAYBOOK, (technique, cohort, metric))
    )


def list_playbook_entries(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PlaybookEntry]:
    return cast(list[PlaybookEntry], _list(conn, _PLAYBOOK, limit=limit, **filters))


# --- legal / learning ----------------------------------------------------------

def save_legal_issue(conn: sqlite3.Connection, issue: LegalIssue) -> str:
    return cast(str, _save(conn, _LEGAL_ISSUES, issue))


def get_legal_issue(conn: sqlite3.Connection, issue_id: str) -> LegalIssue | None:
    return cast(LegalIssue | None, _get(conn, _LEGAL_ISSUES, issue_id))


def list_legal_issues(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LegalIssue]:
    return cast(list[LegalIssue], _list(conn, _LEGAL_ISSUES, limit=limit, **filters))


def save_position(conn: sqlite3.Connection, position: Position) -> str:
    return cast(str, _save(conn, _POSITIONS, position))


def get_position(conn: sqlite3.Connection, position_id: str) -> Position | None:
    return cast(Position | None, _get(conn, _POSITIONS, position_id))


def list_positions(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[Position]:
    return cast(list[Position], _list(conn, _POSITIONS, limit=limit, **filters))


def save_defense_memo(conn: sqlite3.Connection, memo: DefenseMemo) -> str:
    return cast(str, _save(conn, _DEFENSE_MEMOS, memo))


def get_defense_memo(conn: sqlite3.Connection, memo_id: str) -> DefenseMemo | None:
    return cast(DefenseMemo | None, _get(conn, _DEFENSE_MEMOS, memo_id))


def list_defense_memos(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[DefenseMemo]:
    return cast(list[DefenseMemo], _list(conn, _DEFENSE_MEMOS, limit=limit, **filters))


def save_learning_change(conn: sqlite3.Connection, change: LearningChange) -> str:
    return cast(str, _save(conn, _LEARNING_CHANGES, change))


def get_learning_change(conn: sqlite3.Connection, change_id: str) -> LearningChange | None:
    return cast(LearningChange | None, _get(conn, _LEARNING_CHANGES, change_id))


def list_learning_changes(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[LearningChange]:
    return cast(
        list[LearningChange], _list(conn, _LEARNING_CHANGES, limit=limit, **filters)
    )


def save_prompt_trial(conn: sqlite3.Connection, trial: PromptTrial) -> str:
    return cast(str, _save(conn, _PROMPT_TRIALS, trial))


def get_prompt_trial(conn: sqlite3.Connection, trial_id: str) -> PromptTrial | None:
    return cast(PromptTrial | None, _get(conn, _PROMPT_TRIALS, trial_id))


def list_prompt_trials(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[PromptTrial]:
    return cast(list[PromptTrial], _list(conn, _PROMPT_TRIALS, limit=limit, **filters))


# --- infrastructure tables -----------------------------------------------------

_SUMMARY_COLS = ("id", "run_id", "kind", "unit_id", "document_id", "chapter_id", "status")


def save_summary(
    conn: sqlite3.Connection,
    summary_id: str,
    kind: str,
    body: dict[str, Any],
    *,
    run_id: str | None = None,
    unit_id: str | None = None,
    document_id: str | None = None,
    chapter_id: str | None = None,
    status: str | None = None,
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "summaries" ("id", "run_id", "kind", "unit_id",'
            ' "document_id", "chapter_id", "status", "body", "created_at")'
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                summary_id, run_id, kind, unit_id, document_id, chapter_id,
                status, to_json(body), _utcnow(),
            ),
        )
    return summary_id


def get_summary(conn: sqlite3.Connection, summary_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "summaries" WHERE "id" = ?', (summary_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["body"] = from_json(data["body"])
    return data


def list_summaries(
    conn: sqlite3.Connection, *, limit: int | None = None, **filters: Any
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for name, value in filters.items():
        if name not in _SUMMARY_COLS:
            raise ValueError(f"unknown summaries filter {name!r}")
        if value is None:
            continue
        clauses.append(f"{_q(name)} = ?")
        params.append(value)
    sql = 'SELECT * FROM "summaries"'
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["body"] = from_json(data["body"])
        out.append(data)
    return out


def cache_set(
    conn: sqlite3.Connection, key: str, value: str, *, expires_at: str | None = None
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "cache" ("key", "value", "created_at", "expires_at")'
            " VALUES (?, ?, ?, ?)",
            (key, value, _utcnow(), expires_at),
        )
    return key


def cache_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute('SELECT "value" FROM "cache" WHERE "key" = ?', (key,)).fetchone()
    return str(row["value"]) if row is not None else None


def cache_delete(conn: sqlite3.Connection, key: str) -> bool:
    with conn:
        cur = conn.execute('DELETE FROM "cache" WHERE "key" = ?', (key,))
    return cur.rowcount > 0


def save_dead_letter(
    conn: sqlite3.Connection,
    agent: str,
    team: str,
    payload: dict[str, Any],
    error: str,
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "dead_letters" ("run_id", "agent", "team", "payload", "error",'
            ' "created_at") VALUES (?, ?, ?, ?, ?, ?)',
            (run_id, agent, team, to_json(payload), error, _utcnow()),
        )
    return int(cur.lastrowid or 0)


def get_dead_letter(conn: sqlite3.Connection, item_id: int) -> dict[str, Any] | None:
    row = conn.execute('SELECT * FROM "dead_letters" WHERE "id" = ?', (item_id,)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["payload"] = from_json(data["payload"])
    return data


def delete_dead_letter(conn: sqlite3.Connection, item_id: int) -> bool:
    with conn:
        cur = conn.execute('DELETE FROM "dead_letters" WHERE "id" = ?', (item_id,))
    return cur.rowcount > 0


def list_dead_letters(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "dead_letters"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["payload"] = from_json(data["payload"])
        out.append(data)
    return out


def save_checkpoint(
    conn: sqlite3.Connection, key: str, state: dict[str, Any], *, run_id: str | None = None
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "checkpoints" ("key", "run_id", "state", "updated_at")'
            " VALUES (?, ?, ?, ?)",
            (key, run_id, to_json(state), _utcnow()),
        )
    return key


def get_checkpoint(conn: sqlite3.Connection, key: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "checkpoints" WHERE "key" = ?', (key,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["state"] = from_json(data["state"])
    return data


def delete_checkpoint(conn: sqlite3.Connection, key: str) -> bool:
    """Drop a checkpoint (terminal runs leave nothing to resume)."""
    with conn:
        cur = conn.execute('DELETE FROM "checkpoints" WHERE "key" = ?', (key,))
    return cur.rowcount > 0


def append_event(
    conn: sqlite3.Connection,
    event_type: str,
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "events" ("run_id", "type", "payload", "created_at")'
            " VALUES (?, ?, ?, ?)",
            (run_id, event_type, to_json(payload), _utcnow()),
        )
    return int(cur.lastrowid or 0)


def list_events(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "events"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    out: list[dict[str, Any]] = []
    for row in conn.execute(sql, params):
        data = dict(row)
        data["payload"] = from_json(data["payload"])
        out.append(data)
    return out


def save_dialogue(
    conn: sqlite3.Connection,
    dialogue_id: str,
    turns: list[dict[str, Any]],
    status: str,
    *,
    run_id: str | None = None,
    proposal_id: str | None = None,
) -> str:
    with conn:
        conn.execute(
            'INSERT OR REPLACE INTO "dialogues" ("id", "run_id", "proposal_id", "turns",'
            ' "status", "updated_at") VALUES (?, ?, ?, ?, ?, ?)',
            (dialogue_id, run_id, proposal_id, to_json(turns), status, _utcnow()),
        )
    return dialogue_id


def get_dialogue(conn: sqlite3.Connection, dialogue_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        'SELECT * FROM "dialogues" WHERE "id" = ?', (dialogue_id,)
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["turns"] = from_json(data["turns"])
    return data


def save_waiver(
    conn: sqlite3.Connection,
    issue_id: str,
    reason: str,
    decided_by: str,
    *,
    run_id: str | None = None,
) -> int:
    with conn:
        cur = conn.execute(
            'INSERT INTO "waivers" ("run_id", "issue_id", "reason", "decided_by",'
            ' "decided_at") VALUES (?, ?, ?, ?, ?)',
            (run_id, issue_id, reason, decided_by, _utcnow()),
        )
    return int(cur.lastrowid or 0)


def list_waivers(
    conn: sqlite3.Connection, *, run_id: str | None = None, limit: int | None = None
) -> list[dict[str, Any]]:
    sql = 'SELECT * FROM "waivers"'
    params: list[Any] = []
    if run_id is not None:
        sql += ' WHERE "run_id" = ?'
        params.append(run_id)
    sql += " ORDER BY rowid"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return [dict(row) for row in conn.execute(sql, params)]


# --- idempotency (F07) / snapshots (F20) ----------------------------------------

def idempotent_save(conn: sqlite3.Connection, model: BaseModel, key: str) -> bool:
    """Insert-or-ignore on an idempotency key; True when the row was written.

    The first call with a given key persists `model`; later calls with the
    same key leave the stored row untouched and return False.
    """
    try:
        spec = _BY_MODEL[type(model)]
    except KeyError as exc:
        raise ValueError(f"no table registered for {type(model).__name__}") from exc
    with conn:
        cur = conn.execute(
            'INSERT OR IGNORE INTO "idempotency_keys" ("key", "created_at")'
            " VALUES (?, ?)",
            (key, _utcnow()),
        )
        if cur.rowcount == 0:
            return False
    _save(conn, spec, model)
    return True


_RUN_COUNT_TABLES: tuple[str, ...] = tuple(
    sorted(
        {s.table for s in _SPECS if "run_id" in s.model.model_fields}
        | {"summaries", "dead_letters", "checkpoints", "events", "dialogues", "waivers"}
    )
)


def snapshot_counts(conn: sqlite3.Connection, run_id: str) -> dict[str, int]:
    """Per-table row counts for one run, for invariant checks (F20)."""
    counts: dict[str, int] = {}
    for table in _RUN_COUNT_TABLES:
        row = conn.execute(
            f'SELECT COUNT(*) AS n FROM {_q(table)} WHERE "run_id" = ?', (run_id,)
        ).fetchone()
        counts[table] = int(row["n"])
    return counts
