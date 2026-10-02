"""legal sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

legal_app = typer.Typer(help="Legal Chamber (22).", no_args_is_help=True)

@legal_app.command("status")
def legal_status() -> None:
    """Show Legal Chamber status."""
    _not_implemented("P17")

@legal_app.command("issue")
def legal_issue(issue_id: str = typer.Argument(..., help="Issue id.")) -> None:
    """Show a legal issue memo."""
    _not_implemented("P17")

@legal_app.command("waive")
def legal_waive(
    issue_id: str = typer.Argument(..., help="Issue id."),
    attorney_confirmed: bool = typer.Option(
        False, "--attorney-confirmed", help="Required: a human attorney confirmed."
    ),
    reason_text: str = typer.Option(..., "--reason", help="Waiver reason (required)."),
) -> None:
    """Waive a legal issue (requires attorney confirmation + reason)."""
    _ = (attorney_confirmed, reason_text)
    _not_implemented("P17")
