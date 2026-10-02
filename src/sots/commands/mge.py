"""MGE sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

mge_app = typer.Typer(help="Master Grading Engine (27).", no_args_is_help=True)

@mge_app.command("stability")
def mge_stability() -> None:
    """Stability test: re-grade cached artifacts with the cache disabled."""
    _not_implemented("P14M")
