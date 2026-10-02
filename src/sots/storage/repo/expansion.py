"""expansion persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

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
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _CONCEPT_EDGES,
    _CONCEPT_GRAPHS,
    _CONCEPTS,
    _CRITIC_SCORES,
    _DEEP_REPORTS,
    _EXPANSION_THREADS,
    _INTEGRATION_BRIEFS,
    _MARGIN_NOTES,
    _RESEARCH_BRIEFS,
    _RESEARCH_NOTES,
)


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


