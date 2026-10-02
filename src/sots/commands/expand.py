"""expansion sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

expand_app = typer.Typer(help="Stage 11: Expansion Team.", no_args_is_help=True)

@expand_app.command("map")
def expand_map() -> None:
    """Map concepts across all documents."""
    _not_implemented("P18")

@expand_app.command("propose")
def expand_propose() -> None:
    """Propose threads to deepen."""
    _not_implemented("P18")

@expand_app.command("approve")
def expand_approve(thread: str = typer.Argument(..., help="Thread id to approve.")) -> None:
    """Approve a thread for deep research."""
    _not_implemented("P18")

@expand_app.command("research")
def expand_research(thread: str = typer.Argument(..., help="Thread id to research.")) -> None:
    """Run approval-gated deep research on a thread."""
    _not_implemented("P18")

@expand_app.command("dialogue")
def expand_dialogue(doc: str = typer.Argument(..., help="Document id to converse with.")) -> None:
    """Converse with the text (margin notes + chat)."""
    _not_implemented("P18")

@expand_app.command("integrate")
def expand_integrate(rep: str = typer.Argument(..., help="Report id to integrate.")) -> None:
    """Propose how to integrate findings."""
    _not_implemented("P18")
