"""learning sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

learning_app = typer.Typer(help="Learning loop (20 §7).", no_args_is_help=True)

@learning_app.command("inbox")
def learning_inbox() -> None:
    """Show proposed prompt/threshold/persona/rubric changes."""
    _not_implemented("P21")

@learning_app.command("apply")
def learning_apply(change_id: str = typer.Argument(..., help="Change id.")) -> None:
    """Apply a proposed learning change."""
    _not_implemented("P21")

@learning_app.command("rollback")
def learning_rollback(change_id: str = typer.Argument(..., help="Change id.")) -> None:
    """Roll back an applied learning change."""
    _not_implemented("P21")
