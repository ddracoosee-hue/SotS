"""core system commands (init, cost, write, doctor, stop, settings) (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from sots.commands._shared import (
    DATA_DIRS,
    DB_PLACEHOLDER,
    PROFILE_TEMPLATE_FILES,
    VOICE_REGISTERS,
    _template_dir,
)


def init(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Project root to initialise (default: current directory).",
    ),
) -> None:
    """Create data dirs, an empty DB placeholder, and profile templates.

    Idempotent: existing files and directories are never overwritten.
    """
    try:
        templates = _template_dir()
    except typer.Exit:
        print("profile_templates/ not found")
        raise
    created: list[str] = []
    for dirname in DATA_DIRS:
        target = root / dirname
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    db = root / DB_PLACEHOLDER
    if not db.exists():
        db.parent.mkdir(parents=True, exist_ok=True)
        db.touch()
        created.append(str(db))
    for src_rel, dst_rel in PROFILE_TEMPLATE_FILES:
        src = templates / src_rel
        dst = root / dst_rel
        if not dst.exists() and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            created.append(str(dst))
    for register in VOICE_REGISTERS:
        target = root / "profile/voice_corpus" / register
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    if created:
        for item in created:
            print(f"created {item}")
    else:
        print("already initialised; nothing to do")

def cost(
    since: str | None = typer.Option(None, "--since", help="Only include calls since DATE."),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Token and cost summary from llm_calls."""
    from datetime import datetime

    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.providers import calllog
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    since_dt: datetime | None = None
    if since is not None:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            print(f"bad --since date {since!r}; use YYYY-MM-DD")
            raise typer.Exit(code=1) from None
    db_path = root / settings.paths.db_path
    if not db_path.is_file():
        print(f"no database yet at {db_path}")
        raise typer.Exit(code=1)
    conn = storage_db.connect(db_path)
    try:
        storage_db.migrate(conn)
        rows = calllog.summarize(conn, since_dt)
    finally:
        conn.close()
    if not rows:
        print("no LLM calls recorded")
        return
    print(f"{'task':<28}{'provider':<10}{'calls':>6}{'in_tok':>9}{'out_tok':>9}{'cost':>10}")
    total_cost = 0.0
    for row in rows:
        total_cost += row.cost
        print(
            f"{row.task:<28}{row.provider:<10}{row.calls:>6}"
            f"{row.input_tokens:>9}{row.output_tokens:>9}{row.cost:>10.4f}"
        )
    print(f"total cost: {total_cost:.4f}")

def write(ctx: typer.Context) -> None:
    """Free-form drafting (disabled: R-SCOPE-02)."""
    _ = ctx
    print("Writer is disabled (R-SCOPE-02)")
    raise typer.Exit(code=2)

def doctor(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """F17 health check (runs automatically before every act)."""
    import asyncio

    from rich.console import Console

    from sots.agents.failsafes.f17_doctor import format_report, run_doctor

    report = asyncio.run(run_doctor(root))
    Console().print(format_report(report))
    if report.failed:
        raise typer.Exit(code=1)

def stop(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """F16 kill switch: stop the current run immediately."""
    from sots.agents.failsafes.f16_killswitch import engage
    from sots.config import load_settings
    from sots.errors import ConfigError

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    path = engage(root / settings.paths.data_dir)
    print(f"stop requested: {path}")

settings_app = typer.Typer(help="Settings and provider health.", no_args_is_help=True)

@settings_app.command("test-providers")
def settings_test_providers(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Health-check each configured provider and fetcher."""
    import asyncio

    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.providers.router import build_registry

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    registry = build_registry(settings)
    print(f"{'provider':<10}{'status':<16}detail")
    for name, provider in registry.items():
        health = asyncio.run(provider.health())
        status = "not configured"
        if provider.configured:
            status = "ok" if health.ok else "FAILED"
        print(f"{name:<10}{status:<16}{health.detail}")
