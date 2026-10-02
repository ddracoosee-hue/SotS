"""review sub-app (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer

review_app = typer.Typer(help="Review queue stand-in (05 §3.4).", no_args_is_help=True)

@review_app.command("list")
def review_list(
    run_id: str | None = typer.Option(None, "--run-id", help="Only this run."),
    threshold: float | None = typer.Option(
        None, "--threshold", help="Override settings.classify.review_threshold."
    ),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """List units awaiting author review."""
    from sots.classify.review_queue import needs_review
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    db_path = root / settings.paths.db_path
    if not db_path.is_file():
        print(f"no database yet at {db_path}")
        raise typer.Exit(code=1)
    conn = storage_db.connect(db_path)
    try:
        units = needs_review(
            conn, run_id=run_id,
            threshold=threshold if threshold is not None else settings.classify.review_threshold,
        )
        for unit in units:
            print(f"{unit.id} [{unit.classify_confidence}] {unit.text[:80]}")
        print(f"{len(units)} unit(s) need review")
    finally:
        conn.close()

@review_app.command("relabel")
def review_relabel(
    unit_id: str = typer.Argument(..., help="Unit id to relabel."),
    content_type: str | None = typer.Option(None, "--type", help="Content type."),
    claim_kind: str | None = typer.Option(None, "--claim-kind", help="Claim kind."),
    media_kind: str | None = typer.Option(None, "--media-kind", help="Media kind."),
    checkability: str | None = typer.Option(None, "--checkability", help="Checkability."),
    entities: str | None = typer.Option(None, "--entities", help="Comma-separated."),
    normalized_claim: str | None = typer.Option(None, "--claim", help="Normalized claim."),
    confidence: float | None = typer.Option(None, "--confidence", help="Confidence."),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Relabel a unit as the author (never overwritten by re-runs)."""
    from pydantic import ValidationError

    from sots.classify.review_queue import relabel
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    db_path = root / settings.paths.db_path
    if not db_path.is_file():
        print(f"no database yet at {db_path}")
        raise typer.Exit(code=1)
    fields: dict[str, object] = {}
    if content_type is not None:
        fields["content_type"] = content_type
    if claim_kind is not None:
        fields["claim_kind"] = claim_kind
    if media_kind is not None:
        fields["media_kind"] = media_kind
    if checkability is not None:
        fields["checkability"] = checkability
    if entities is not None:
        fields["entities"] = [e.strip() for e in entities.split(",") if e.strip()]
    if normalized_claim is not None:
        fields["normalized_claim"] = normalized_claim
    if confidence is not None:
        fields["classify_confidence"] = confidence
    conn = storage_db.connect(db_path)
    try:
        try:
            updated = relabel(conn, unit_id, fields)
        except (KeyError, ValueError, ValidationError) as exc:
            print(f"relabel failed: {exc}")
            raise typer.Exit(code=1) from exc
        print(f"relabeled {updated.id} as {updated.content_type} (author)")
    finally:
        conn.close()
