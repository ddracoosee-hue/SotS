"""document ingest command (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer


def ingest(
    path: Path = typer.Argument(..., help="File to ingest."),
    chapter: str | None = typer.Option(None, "--chapter", help="Chapter id, e.g. ch03."),
    title: str | None = typer.Option(None, "--title", help="Document title."),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Stage 1: ingest a document. Prints the doc_id."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.ingest.ingest import ingest_file
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    inbox_dir = root / settings.paths.inbox_dir
    db_path = root / settings.paths.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = storage_db.connect(db_path)
    try:
        storage_db.migrate(conn)
        try:
            outcome = ingest_file(
                path, conn=conn, inbox_dir=inbox_dir, title=title, chapter_id=chapter
            )
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            print(f"ingest failed: {exc}")
            raise typer.Exit(code=1) from exc
        if outcome.duplicate_of is not None and not typer.confirm(
            f"Duplicate of {outcome.duplicate_of}. Reuse it?", default=True
        ):
            outcome = ingest_file(
                path, conn=conn, inbox_dir=inbox_dir, title=title,
                chapter_id=chapter, allow_duplicate=True,
            )
        for warning in outcome.warnings:
            print(f"warning: {warning}")
        print(outcome.document.id)
    finally:
        conn.close()
