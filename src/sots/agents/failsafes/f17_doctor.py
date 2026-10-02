"""F17 doctor: pre-run health checks (P03 T03.056, 16 §5.1).

Checks config, cards, prompts, providers, tools, keys, disk space, DB
integrity, and the LanguageTool server. Hard failures fail the report
(`sots doctor` exits 1); missing keys and an unreachable LanguageTool are
warnings. Runs automatically before every act (orchestrators call this).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict
from rich.table import Table

from sots.config import ENV_SECRET_MAP, Settings, load_settings
from sots.errors import ConfigError

Status = Literal["ok", "warn", "fail"]

MIN_FREE_BYTES = 1_000_000_000


class CheckResult(BaseModel):
    """One doctor check outcome."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    status: Status
    detail: str


class DoctorReport(BaseModel):
    """Full doctor outcome; `failed` is True on any hard failure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    checks: list[CheckResult]

    @property
    def failed(self) -> bool:
        """True when any check hard-failed."""
        return any(check.status == "fail" for check in self.checks)


async def run_doctor(root: str | Path) -> DoctorReport:
    """Run every check against the project `root`."""
    project = Path(root)
    checks: list[CheckResult] = []
    settings: Settings | None = None
    try:
        settings = load_settings(project / "config")
        checks.append(CheckResult(name="config", status="ok", detail="settings valid"))
    except ConfigError as exc:
        checks.append(CheckResult(name="config", status="fail", detail=str(exc)))
        return DoctorReport(checks=checks)
    assert settings is not None
    checks.append(_check_routing(project))
    checks.append(_check_cards(project, settings))
    checks.append(_check_foundation(project, settings))
    checks.append(_check_prompts(project, settings))
    checks.append(await _check_providers(settings))
    checks.append(_check_tools())
    checks.append(_check_keys(settings))
    checks.append(_check_disk(project))
    checks.append(_check_database(project, settings))
    checks.append(await _check_languagetool(settings))
    return DoctorReport(checks=checks)


def _check_routing(project: Path) -> CheckResult:
    from sots.providers.router import load_routing

    try:
        routing = load_routing(project / "config" / "routing.yaml")
    except ConfigError as exc:
        return CheckResult(name="routing", status="fail", detail=str(exc))
    return CheckResult(
        name="routing", status="ok", detail=f"{len(routing.tasks)} tasks"
    )


def _check_cards(project: Path, settings: Settings) -> CheckResult:
    import sots.agents.tools  # noqa: F401  (register every tool)
    from sots.agents.cards import load_cards
    from sots.agents.tools.base import registered_tools
    from sots.providers.router import load_routing

    try:
        routing = load_routing(project / "config" / "routing.yaml")
        cards = load_cards(
            project / "config" / "agents",
            prompts_dir=project / settings.paths.prompts_dir,
            routing=routing,
            tools=registered_tools(),
        )
    except ConfigError as exc:
        return CheckResult(name="cards", status="fail", detail=str(exc))
    from sots.agents.cards import cards_missing_foundation

    omitting = cards_missing_foundation(cards)
    if omitting:
        return CheckResult(
            name="cards", status="warn",
            detail=f"{len(cards)} cards valid; R-FOUND-01: {', '.join(omitting)} omit F1/F2",
        )
    return CheckResult(name="cards", status="ok", detail=f"{len(cards)} cards valid")


def _check_foundation(project: Path, settings: Settings) -> CheckResult:
    """Foundation files valid (P04A T04A.013; same loader as `foundation check`)."""
    from sots.foundation.loader import load_foundation

    profile_dir = project / settings.paths.profile_dir
    if not profile_dir.is_dir():
        return CheckResult(
            name="foundation", status="warn", detail="profile not initialized"
        )
    try:
        foundation = load_foundation(profile_dir)
    except Exception as exc:
        return CheckResult(
            name="foundation", status="fail", detail=f"loader crashed: {exc}"
        )
    if foundation.errors:
        return CheckResult(
            name="foundation", status="fail",
            detail=f"{len(foundation.errors)} errors (first: {foundation.errors[0]})",
        )
    return CheckResult(
        name="foundation", status="ok",
        detail=f"{len(foundation.anchors)} anchors,"
        f" {len(foundation.briefs)}/12 briefs parsed",
    )


def _check_prompts(project: Path, settings: Settings) -> CheckResult:
    prompts_dir = project / settings.paths.prompts_dir
    if not prompts_dir.is_dir():
        return CheckResult(name="prompts", status="fail", detail=f"{prompts_dir} missing")
    count = sum(1 for _ in prompts_dir.rglob("*.md"))
    return CheckResult(name="prompts", status="ok", detail=f"{count} prompt files")


async def _check_providers(settings: Settings) -> CheckResult:
    from sots.providers.router import build_registry

    registry = build_registry(settings)
    parts: list[str] = []
    failed = False
    for name, provider in registry.items():
        if not provider.configured:
            parts.append(f"{name}: not configured")
            continue
        health = await provider.health()
        if health.ok:
            parts.append(f"{name}: ok")
        else:
            failed = True
            parts.append(f"{name}: FAILED ({health.detail})")
    if failed:
        return CheckResult(name="providers", status="fail", detail="; ".join(parts))
    if any("not configured" in part for part in parts):
        return CheckResult(name="providers", status="warn", detail="; ".join(parts))
    return CheckResult(name="providers", status="ok", detail="; ".join(parts))


def _check_tools() -> CheckResult:
    import sots.agents.tools  # noqa: F401  (register every tool)
    from sots.agents.tools.base import registered_tools
    from sots.agents.tools.structured_lookups import LOOKUP_TOOLS

    expected = {
        "compute", "db_read_units", "db_read_evidence", "db_read_findings",
        "db_read_profile", "excerpt_verify", "fetch_url", "parse_html", "parse_pdf",
        "parse_table", "web_search", "languagetool", *LOOKUP_TOOLS,
    }
    missing = sorted(expected - set(registered_tools()))
    if missing:
        return CheckResult(
            name="tools", status="fail", detail=f"missing: {', '.join(missing)}"
        )
    return CheckResult(name="tools", status="ok", detail=f"{len(expected)} tools registered")


def _check_keys(settings: Settings) -> CheckResult:
    missing = [
        var for var, field in ENV_SECRET_MAP.items()
        if not getattr(settings.secrets, field)
    ]
    if missing:
        return CheckResult(
            name="keys", status="warn", detail=f"missing: {', '.join(missing)}"
        )
    return CheckResult(name="keys", status="ok", detail="all secrets present")


def _check_disk(project: Path) -> CheckResult:
    free = shutil.disk_usage(project).free
    if free < MIN_FREE_BYTES:
        return CheckResult(
            name="disk", status="fail", detail=f"only {free / 1e9:.2f} GB free"
        )
    return CheckResult(name="disk", status="ok", detail=f"{free / 1e9:.1f} GB free")


def _check_database(project: Path, settings: Settings) -> CheckResult:
    from sots.storage import db as storage_db

    db_path = project / settings.paths.db_path
    if not db_path.is_file():
        return CheckResult(
            name="database", status="warn", detail="not initialized (run sots init)"
        )
    try:
        verdict = storage_db.integrity_check(db_path)
    except Exception as exc:
        return CheckResult(name="database", status="fail", detail=f"unreadable: {exc}")
    if verdict != "ok":
        return CheckResult(
            name="database", status="fail", detail=f"integrity_check: {verdict}"
        )
    return CheckResult(name="database", status="ok", detail="integrity_check ok")


async def _check_languagetool(settings: Settings) -> CheckResult:
    from sots.agents.tools.languagetool import ping

    url = settings.languagetool.url.rstrip("/")
    try:
        await ping(url)
    except Exception as exc:
        return CheckResult(
            name="languagetool", status="warn", detail=f"unreachable: {exc}"
        )
    return CheckResult(name="languagetool", status="ok", detail=f"reachable at {url}")


def format_report(report: DoctorReport) -> Table:
    """Colored Rich table for `sots doctor` (green/yellow/red statuses)."""
    table = Table(title="sots doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    colors = {"ok": "green", "warn": "yellow", "fail": "red"}
    for check in report.checks:
        table.add_row(check.name, f"[{colors[check.status]}]{check.status}[/]", check.detail)
    return table
