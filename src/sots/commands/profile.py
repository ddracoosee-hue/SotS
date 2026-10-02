"""profile sub-app (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer

profile_app = typer.Typer(help="Author and book profile commands.", no_args_is_help=True)

@profile_app.command("interview")
def profile_interview(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Guided interview: writes profile/author.md and profile/book.md."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.profile.interview import run_interview

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    run_interview(root / settings.paths.profile_dir)

@profile_app.command("check")
def profile_check(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Validate the profile files and list what is missing."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.profile.validate import check_profile

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    report = check_profile(root / settings.paths.profile_dir)
    if not report.findings:
        print("profile ok")
        return
    for finding in report.findings:
        print(f"[{finding.severity}] {finding.message}")
    if not report.ok:
        raise typer.Exit(code=1)
