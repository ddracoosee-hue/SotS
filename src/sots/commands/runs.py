"""run and report commands (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)


def run(
    doc_ids: list[str] = typer.Argument(..., help="Document ids to process."),
    stages: str | None = typer.Option(None, "--stages", help="Stage range, e.g. 2-9."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the token/cost estimate only."),
    budget: int | None = typer.Option(None, "--budget", help="Token budget override."),
) -> None:
    """Run the pipeline (Act I) over one or more documents."""
    _not_implemented("P13")

def resume(run_id: str = typer.Argument(..., help="Run id to continue.")) -> None:
    """Continue a stopped or failed run (R-CODE-06)."""
    _not_implemented("P13")

def status(run_id: str | None = typer.Argument(None, help="Run id (default: latest).")) -> None:
    """Show the stage table, unit counts, and tokens used."""
    _not_implemented("P13")

def report(
    run_id: str = typer.Argument(..., help="Run id to report on."),
    open_report: bool = typer.Option(False, "--open", help="Open the report after writing."),
) -> None:
    """Write data/runs/<run_id>/report.md + report.json."""
    _not_implemented("P13")

def claims(
    run_id: str = typer.Argument(..., help="Run id to inspect."),
    verdict: str | None = typer.Option(None, "--verdict", help="Filter by verdict."),
    kind: str | None = typer.Option(None, "--kind", help="Filter by claim kind."),
) -> None:
    """Print a filtered claims table."""
    _not_implemented("P08")

def audit() -> None:
    """System audit (10 §3)."""
    _not_implemented("P24")

def eval() -> None:  # CLI command name is fixed by blueprint 12 §1
    """Run the gold-set evaluation (14)."""
    _not_implemented("P23")

def tui() -> None:
    """Launch the Textual TUI."""
    _not_implemented("P22")
