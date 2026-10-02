"""chapter sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

chapter_app = typer.Typer(help="Per-chapter act state.", no_args_is_help=True)

@chapter_app.command("status")
def chapter_status(
    chapter_id: str | None = typer.Argument(None, help="Chapter id (default: all)."),
) -> None:
    """Show act, gates, and blocked reasons per chapter."""
    _not_implemented("P13")
