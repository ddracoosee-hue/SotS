"""act orchestration commands (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)


def act(
    act_id: str = typer.Argument(..., help="Act to run: II, III, IV, V, or VI."),
    chapter_id: str = typer.Argument(..., help="Chapter id, e.g. ch03."),
) -> None:
    """Run a specific act for a chapter."""
    _not_implemented("P13")

def advance(chapter_id: str = typer.Argument(..., help="Chapter id, e.g. ch03.")) -> None:
    """Run the next eligible act for a chapter."""
    _not_implemented("P13")

def export(target: str = typer.Argument(..., help="Chapter id or 'all'.")) -> None:
    """Master output (19 §6)."""
    _not_implemented("P20")

def replay(run_id: str = typer.Argument(..., help="Run id to replay.")) -> None:
    """F18 deterministic replay of a run."""
    _not_implemented("P03")

def reason(
    scope: str = typer.Option("book", "--scope", help="Scope: book, phase, or chNN."),
    focus: str = typer.Option("both", "--focus", help="Focus: structure, ideas, or both."),
) -> None:
    """Recheck & Reason: re-examine structure and ideas (26)."""
    _not_implemented("P21A")

def revise(
    artifact_id: str = typer.Argument(..., help="Artifact id to revise."),
    note: str = typer.Option(..., "--note", help="Revision note (required)."),
) -> None:
    """Revise an artifact with a recorded note (R-MGE-04)."""
    _not_implemented("P20")

def master_audit(
    sections: str | None = typer.Option(None, "--sections", help="Sections to audit."),
    book: bool = typer.Option(False, "--book", help="Audit the whole book."),
) -> None:
    """Master Audit battery over the book (28)."""
    _not_implemented("P24")
