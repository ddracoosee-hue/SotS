"""Scoped read-only DB tools (P03 T03.027, 16 §3).

`db_read_units` / `db_read_evidence` / `db_read_findings` / `db_read_profile`.
Every id is checked against `ctx.run_id` (+ `ctx.document_id` when set);
any out-of-scope id fails the whole call closed (ok=False listing the denied
ids). Agents never write; these tools only read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


def _require_conn(ctx: ToolContext) -> Connection | Observation:
    if ctx.conn is None:
        return Observation(
            tool="db_read", ok=False, content="error: no database in tool context",
            truncated=False,
        )
    return ctx.conn


def _denied(tool: str, ids: list[str]) -> Observation:
    return Observation(
        tool=tool, ok=False,
        content=f"error: access denied for out-of-scope ids: {', '.join(sorted(ids))}",
        truncated=False,
    )


def _unit_in_scope(ctx: ToolContext, unit: Any) -> bool:
    if unit.run_id != ctx.run_id:
        return False
    return ctx.document_id is None or unit.document_id == ctx.document_id


class DbReadUnitsArgs(BaseModel):
    """Unit ids to read (must belong to this run/document)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_ids: list[str]


class DbReadUnitsTool:
    """`db_read_units`: scoped unit reads (16 §3)."""

    name = "db_read_units"
    internet = False
    args_model = DbReadUnitsArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, DbReadUnitsArgs)
        conn = _require_conn(ctx)
        if isinstance(conn, Observation):
            return conn
        units: list[dict[str, Any]] = []
        denied: list[str] = []
        missing: list[str] = []
        for unit_id in args.unit_ids:
            unit = storage_repo.get_unit(conn, unit_id)
            if unit is None:
                missing.append(unit_id)
            elif not _unit_in_scope(ctx, unit):
                denied.append(unit_id)
            else:
                units.append(unit.model_dump(mode="json"))
        if denied:
            return _denied(self.name, denied)
        payload = {"units": units, "missing": missing}
        return Observation(tool=self.name, ok=True, content=json.dumps(payload), truncated=False)


class DbReadEvidenceArgs(BaseModel):
    """Evidence by unit ids and/or evidence ids (at least one required)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_ids: list[str] | None = None
    evidence_ids: list[str] | None = None


class DbReadEvidenceTool:
    """`db_read_evidence`: evidence scoped through its unit (16 §3)."""

    name = "db_read_evidence"
    internet = False
    args_model = DbReadEvidenceArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, DbReadEvidenceArgs)
        conn = _require_conn(ctx)
        if isinstance(conn, Observation):
            return conn
        if not args.unit_ids and not args.evidence_ids:
            return Observation(
                tool=self.name, ok=False,
                content="error: provide unit_ids and/or evidence_ids", truncated=False,
            )
        denied_units: list[str] = []
        for unit_id in args.unit_ids or []:
            unit = storage_repo.get_unit(conn, unit_id)
            if unit is not None and not _unit_in_scope(ctx, unit):
                denied_units.append(unit_id)
        if denied_units:
            return _denied(self.name, denied_units)
        wanted: dict[str, Any] = {}
        for evidence_id in args.evidence_ids or []:
            row = storage_repo.get_evidence(conn, evidence_id)
            if row is not None:
                wanted[row.id] = row
        for unit_id in args.unit_ids or []:
            for row in storage_repo.list_evidence(conn, unit_id=unit_id):
                wanted[row.id] = row
        evidence: list[dict[str, Any]] = []
        denied: list[str] = []
        for row in wanted.values():
            unit = storage_repo.get_unit(conn, row.unit_id)
            if unit is None or not _unit_in_scope(ctx, unit):
                denied.append(row.id)
            else:
                evidence.append(row.model_dump(mode="json"))
        if denied:
            return _denied(self.name, denied)
        return Observation(
            tool=self.name, ok=True, content=json.dumps({"evidence": evidence}), truncated=False
        )


class DbReadFindingsArgs(BaseModel):
    """Specialist findings by unit ids."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_ids: list[str]


class DbReadFindingsTool:
    """`db_read_findings`: findings scoped through their unit (16 §3)."""

    name = "db_read_findings"
    internet = False
    args_model = DbReadFindingsArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, DbReadFindingsArgs)
        conn = _require_conn(ctx)
        if isinstance(conn, Observation):
            return conn
        findings: list[dict[str, Any]] = []
        denied: list[str] = []
        for unit_id in args.unit_ids:
            unit = storage_repo.get_unit(conn, unit_id)
            if unit is not None and not _unit_in_scope(ctx, unit):
                denied.append(unit_id)
                continue
            for row in storage_repo.list_specialist_findings(conn, unit_id=unit_id):
                findings.append(row.model_dump(mode="json"))
        if denied:
            return _denied(self.name, denied)
        return Observation(
            tool=self.name, ok=True, content=json.dumps({"findings": findings}), truncated=False
        )


class DbReadProfileArgs(BaseModel):
    """Foundation messages: whole book, or one chapter's slice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter: str | None = None


def _read_messages(profile_dir: str) -> dict[str, Any]:
    path = Path(profile_dir) / "messages.yaml"
    if not path.is_file():
        raise ValueError(f"messages.yaml not found in {profile_dir}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


class DbReadProfileTool:
    """`db_read_profile`: book/chapter messages (provisional file read; P04A owns it)."""

    name = "db_read_profile"
    internet = False
    args_model = DbReadProfileArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, DbReadProfileArgs)
        try:
            messages = _read_messages(ctx.profile_dir)
        except (ValueError, OSError) as exc:
            return Observation(tool=self.name, ok=False, content=f"error: {exc}", truncated=False)
        if args.chapter is None:
            payload = {"book": messages.get("book", [])}
        else:
            chapters = messages.get("chapters") or {}
            if args.chapter not in chapters:
                return Observation(
                    tool=self.name, ok=False,
                    content=f"error: unknown chapter {args.chapter!r}", truncated=False,
                )
            payload = {"book": messages.get("book", []), args.chapter: chapters[args.chapter]}
        return Observation(tool=self.name, ok=True, content=json.dumps(payload), truncated=False)


register_tool(DbReadUnitsTool())
register_tool(DbReadEvidenceTool())
register_tool(DbReadFindingsTool())
register_tool(DbReadProfileTool())
