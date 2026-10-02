"""hunks sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

hunks_app = typer.Typer(help="Hunk-by-hunk review (Pass B).", no_args_is_help=True)

@hunks_app.command("review")
def hunks_review(revision_id: str = typer.Argument(..., help="Revision id.")) -> None:
    """Terminal hunk-by-hunk accept/reject."""
    _not_implemented("P20")
