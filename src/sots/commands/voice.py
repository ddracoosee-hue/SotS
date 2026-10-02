"""voice sub-app (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer

from sots.commands._shared import (
    _not_implemented,
)

voice_app = typer.Typer(help="Voice Lab (29).", no_args_is_help=True)

@voice_app.command("add")
def voice_add(
    path: Path = typer.Argument(..., help="File or folder to add."),
    register: str = typer.Option(..., "--register", help="final, draft, spoken, or casual."),
    weight: float = typer.Option(1.0, "--weight", help="Trust weight 0.5-2.0."),
    note: str | None = typer.Option(None, "--note", help="Note about this material."),
) -> None:
    """Add writing to the voice corpus."""
    _ = (register, weight, note)
    _not_implemented("P11A")

@voice_app.command("sync")
def voice_sync() -> None:
    """Register files dropped directly into voice_corpus/ folders."""
    _not_implemented("P11A")

@voice_app.command("profile")
def voice_profile() -> None:
    """Show the Voice Profile (top features, confidence bars)."""
    _not_implemented("P11A")

@voice_app.command("check")
def voice_check(
    text: str | None = typer.Argument(None, help="Text to check (or paste at the prompt)."),
) -> None:
    """'Does this sound like me?' check with sentence highlights."""
    _ = text
    _not_implemented("P11A")

@voice_app.command("pin")
def voice_pin(feature: str = typer.Argument(..., help="Feature to pin as core.")) -> None:
    """Pin a voice feature as core (always keep)."""
    _not_implemented("P11A")

@voice_app.command("relax")
def voice_relax(feature: str = typer.Argument(..., help="Feature to relax.")) -> None:
    """Relax a voice feature (the author is trying to change it)."""
    _not_implemented("P11A")

@voice_app.command("forbid")
def voice_forbid(pattern: str = typer.Argument(..., help="Pattern to forbid.")) -> None:
    """Forbid a pattern (never write it)."""
    _not_implemented("P11A")

@voice_app.command("snapshot")
def voice_snapshot() -> None:
    """Snapshot the current Voice Model version."""
    _not_implemented("P11A")

@voice_app.command("rollback")
def voice_rollback(version: str = typer.Argument(..., help="Version to roll back to.")) -> None:
    """Roll the Voice Model back to a snapshot."""
    _not_implemented("P11A")
