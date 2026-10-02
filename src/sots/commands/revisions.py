"""revisions sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

revisions_app = typer.Typer(help="Revision history.", no_args_is_help=True)

@revisions_app.command("list")
def revisions_list(chapter_id: str = typer.Argument(..., help="Chapter id.")) -> None:
    """List revisions for a chapter."""
    _not_implemented("P15")

@revisions_app.command("diff")
def revisions_diff(
    rev_a: str = typer.Argument(..., help="First revision id."),
    rev_b: str = typer.Argument(..., help="Second revision id."),
) -> None:
    """Diff two revisions."""
    _not_implemented("P15")
