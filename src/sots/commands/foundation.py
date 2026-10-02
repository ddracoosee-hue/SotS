"""foundation sub-app (W0 split of cli.py)."""
# ruff: noqa: B008 - typer.Option/Argument in defaults is idiomatic.

from __future__ import annotations

from pathlib import Path

import typer

foundation_app = typer.Typer(help="Book Foundation commands (23).", no_args_is_help=True)

@foundation_app.command("parse")
def foundation_parse(
    chapter: str = typer.Argument(..., help="Chapter id (ch03) or 'all'."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Re-parse existing yamls."),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Parse chapter brief(s) to structured chNN.yaml files (23 §2)."""
    import asyncio
    import difflib
    import uuid

    import yaml

    from sots.config import load_settings
    from sots.errors import ConfigError, ProviderNotConfiguredError, ValidationFailedError
    from sots.foundation.anchors import AnchorRegistry
    from sots.foundation.brief_parser import parse_brief
    from sots.foundation.loader import CHAPTER_IDS, load_foundation
    from sots.providers.router import build_registry, load_routing
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    profile_dir = root / settings.paths.profile_dir
    chapters_dir = profile_dir / "chapters"
    if chapter != "all" and chapter not in CHAPTER_IDS:
        print(f"unknown chapter {chapter!r} (want ch01-ch12 or 'all')")
        raise typer.Exit(code=1)
    wanted = CHAPTER_IDS if chapter == "all" else [chapter]
    targets = [c for c in wanted if (chapters_dir / f"{c}_brief.md").is_file()]
    if not targets:
        print("no brief files found")
        raise typer.Exit(code=1)
    existing = [c for c in targets if (chapters_dir / f"{c}.yaml").is_file()]
    if existing and not overwrite:
        print(f"exists, use --overwrite: {', '.join(f'{c}.yaml' for c in existing)}")
        targets = [c for c in targets if c not in existing]
        if not targets:
            return
    if existing and overwrite and not typer.confirm(
        f"Re-parse {len(existing)} existing brief(s)?", default=False
    ):
        print("aborted")
        return
    foundation = load_foundation(profile_dir)
    if foundation.errors:
        print(f"foundation has errors: {foundation.errors[0]}")
        raise typer.Exit(code=1)
    registry = AnchorRegistry(foundation.anchors)
    routing = load_routing(root / "config" / "routing.yaml")
    providers = build_registry(settings)
    db_path = root / settings.paths.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = storage_db.connect(db_path)
    failures = 0
    try:
        storage_db.migrate(conn)
        for target in targets:
            yaml_path = chapters_dir / f"{target}.yaml"
            old_text = yaml_path.read_text(encoding="utf-8") if yaml_path.is_file() else None
            brief_text = (chapters_dir / f"{target}_brief.md").read_text(encoding="utf-8")
            try:
                brief, report = asyncio.run(parse_brief(
                    target, brief_text, registry=registry,
                    run_id=f"parse-{uuid.uuid4().hex[:8]}", conn=conn,
                    settings=settings, routing=routing, providers=providers,
                    prompts_dir=root / settings.paths.prompts_dir,
                    brief_path=str(chapters_dir / f"{target}_brief.md"),
                ))
            except (ProviderNotConfiguredError, ValidationFailedError) as exc:
                print(f"{target}: failed: {exc}")
                failures += 1
                continue
            new_text = yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False)
            yaml_path.write_text(new_text, encoding="utf-8")
            if old_text is not None:
                diff = difflib.unified_diff(
                    old_text.splitlines(), new_text.splitlines(),
                    f"a/{target}.yaml", f"b/{target}.yaml", lineterm="",
                )
                print("\n".join(diff))
            print(f"wrote {target}.yaml", end="")
            if report.unregistered_anchors:
                print(f" (+{len(report.unregistered_anchors)} unregistered anchors):")
                for item in report.unregistered_anchors:
                    print(f"  B{item.block}: {item.text[:80]}")
            else:
                print(" (0 unregistered anchors)")
    finally:
        conn.close()
    if failures:
        raise typer.Exit(code=1)

@foundation_app.command("check")
def foundation_check(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Validate every foundation file (23 §1); used by `sots doctor`."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.foundation.loader import load_foundation

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    foundation = load_foundation(root / settings.paths.profile_dir)
    if foundation.errors:
        for error in foundation.errors:
            print(f"[error] {error}")
        raise typer.Exit(code=1)
    parsed = len(foundation.briefs)
    print(
        f"foundation ok: {len(foundation.anchors)} anchors,"
        f" {parsed}/12 briefs parsed"
    )
