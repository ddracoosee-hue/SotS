"""proposals_rewrite persistence (W0 split of storage/repo.py)."""

from __future__ import annotations

import sqlite3
from typing import Any, cast

from sots.models.proposal import (
    IntegrationPlanItem,
    Proposal,
    ProposalDecision,
)
from sots.models.rewrite import (
    CrossCheckReport,
    Revision,
    RevisionHunk,
    StyleGuide,
    StyleReport,
)
from sots.storage.repo._core import _get, _list, _save
from sots.storage.repo._specs import (
    _CROSS_CHECK_REPORTS,
    _PLAN_ITEMS,
    _PROPOSAL_DECISIONS,
    _PROPOSALS,
    _REVISION_HUNKS,
    _REVISIONS,
    _STYLE_GUIDES,
    _STYLE_REPORTS,
)


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


