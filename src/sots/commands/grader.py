"""grader sub-app (W0 split of cli.py)."""


from __future__ import annotations

import typer

from sots.commands._shared import (
    _not_implemented,
)

grader_app = typer.Typer(help="Quality gate grader (17).", no_args_is_help=True)

@grader_app.command("health")
def grader_health() -> None:
    """Grader calibration signals (17 §6)."""
    _not_implemented("P14")
