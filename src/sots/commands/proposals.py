"""proposals sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

proposals_app = typer.Typer(help="Proposal Desk (18).", no_args_is_help=True)

@proposals_app.command("list")
def proposals_list() -> None:
    """List open proposals."""
    _not_implemented("P19")

@proposals_app.command("show")
def proposals_show(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Show a proposal card."""
    _not_implemented("P19")

@proposals_app.command("decide")
def proposals_decide(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Record a decision on a proposal."""
    _not_implemented("P19")

@proposals_app.command("archive")
def proposals_archive(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Archive a proposal."""
    _not_implemented("P19")
