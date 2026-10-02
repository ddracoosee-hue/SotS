"""Shared CLI helpers and constants (W0 split of cli.py)."""

from __future__ import annotations

from pathlib import Path

import typer

DATA_DIRS = ("data", "data/inbox", "data/cache", "data/runs", "data/logs", "data/exports")
DB_PLACEHOLDER = "data/sots.db"
VOICE_REGISTERS = ("final", "drafts", "spoken", "casual", "pairs", "not_me")
PROFILE_TEMPLATE_FILES = (
    ("author.md", "profile/author.md"),
    ("book.md", "profile/book.md"),
    ("messages.yaml", "profile/messages.yaml"),
    ("chapters/README.md", "profile/chapters/README.md"),
    ("voice_corpus/README.md", "profile/voice_corpus/README.md"),
    ("voice_corpus/manifest.yaml", "profile/voice_corpus/manifest.yaml"),
)

def _not_implemented(phase: str) -> None:
    """Print the standard stub notice and exit 1."""
    print(f"not yet implemented (phase {phase})")
    raise typer.Exit(code=1)


def _template_dir() -> Path:
    """Locate the profile_templates/ directory (CWD, repo root, or package dir)."""
    here = Path(__file__).resolve()
    for candidate in (
        Path.cwd() / "profile_templates",
        # parents[3]: this module sits one level deeper than cli.py did (W0
        # split); [3] resolves to the same repo root [2] did before.
        here.parents[3] / "profile_templates",
        here.parent / "profile_templates",
    ):
        if candidate.is_dir():
            return candidate
    raise typer.Exit(code=1)
