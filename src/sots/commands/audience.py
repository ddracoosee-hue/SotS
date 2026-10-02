"""audience sub-app (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer

from sots.commands._shared import (
    _not_implemented,
)

audience_app = typer.Typer(help="Audience Lab (20).", no_args_is_help=True)

@audience_app.command("run")
def audience_run(revision_id: str = typer.Argument(..., help="Revision id.")) -> None:
    """Run the simulated-reader panel on a revision."""
    _not_implemented("P16")

@audience_app.command("import")
def audience_import(csv: Path = typer.Argument(..., help="CSV file to import.")) -> None:
    """Import audience data from CSV."""
    _not_implemented("P16")

@audience_app.command("questionnaire")
def audience_questionnaire() -> None:
    """Show the audience questionnaire."""
    _not_implemented("P16")
