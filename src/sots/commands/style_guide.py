"""style-guide sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

style_guide_app = typer.Typer(help="Style Guide lifecycle (19 §1.2).", no_args_is_help=True)

@style_guide_app.command("build")
def style_guide_build() -> None:
    """Build the Style Guide from the Voice Model."""
    _not_implemented("P15")

@style_guide_app.command("show")
def style_guide_show() -> None:
    """Show the current Style Guide."""
    _not_implemented("P15")

@style_guide_app.command("approve")
def style_guide_approve() -> None:
    """Approve the current Style Guide."""
    _not_implemented("P15")
