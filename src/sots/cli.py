"""SotS command-line interface (P00 T00.050-T00.051, P03 doctor/stop).

Every command and subcommand from blueprint 12 §1, §3.1, and §4 is registered.
Implemented: ``init``, ``cost``, ``settings test-providers``, ``doctor``,
``stop``, ``profile interview``, ``profile check``, ``ingest``,
``foundation parse``, ``foundation check``, and the ``vault`` app.
Every other command is a stub that prints
``not yet implemented (phase Pxx)`` and exits 1, except ``write`` which prints
the R-SCOPE-02 notice and exits 2.
"""

# ruff: noqa: B008 - typer.Option/typer.Argument in defaults is the idiomatic Typer pattern.

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from sots.vault.cli import vault_app

app = typer.Typer(
    name="sots",
    help="The Subject of the Self research and manuscript workflow.",
    no_args_is_help=True,
)

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
        here.parents[2] / "profile_templates",
        here.parent / "profile_templates",
    ):
        if candidate.is_dir():
            return candidate
    raise typer.Exit(code=1)


@app.command()
def init(
    root: Path = typer.Option(
        Path("."),
        "--root",
        help="Project root to initialise (default: current directory).",
    ),
) -> None:
    """Create data dirs, an empty DB placeholder, and profile templates.

    Idempotent: existing files and directories are never overwritten.
    """
    try:
        templates = _template_dir()
    except typer.Exit:
        print("profile_templates/ not found")
        raise
    created: list[str] = []
    for dirname in DATA_DIRS:
        target = root / dirname
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    db = root / DB_PLACEHOLDER
    if not db.exists():
        db.parent.mkdir(parents=True, exist_ok=True)
        db.touch()
        created.append(str(db))
    for src_rel, dst_rel in PROFILE_TEMPLATE_FILES:
        src = templates / src_rel
        dst = root / dst_rel
        if not dst.exists() and src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            created.append(str(dst))
    for register in VOICE_REGISTERS:
        target = root / "profile/voice_corpus" / register
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
            created.append(str(target))
    if created:
        for item in created:
            print(f"created {item}")
    else:
        print("already initialised; nothing to do")


@app.command()
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


@app.command()
def run(
    doc_ids: list[str] = typer.Argument(..., help="Document ids to process."),
    stages: str | None = typer.Option(None, "--stages", help="Stage range, e.g. 2-9."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the token/cost estimate only."),
    budget: int | None = typer.Option(None, "--budget", help="Token budget override."),
) -> None:
    """Run the pipeline (Act I) over one or more documents."""
    _not_implemented("P13")


@app.command()
def resume(run_id: str = typer.Argument(..., help="Run id to continue.")) -> None:
    """Continue a stopped or failed run (R-CODE-06)."""
    _not_implemented("P13")


@app.command()
def status(run_id: str | None = typer.Argument(None, help="Run id (default: latest).")) -> None:
    """Show the stage table, unit counts, and tokens used."""
    _not_implemented("P13")


@app.command()
def report(
    run_id: str = typer.Argument(..., help="Run id to report on."),
    open_report: bool = typer.Option(False, "--open", help="Open the report after writing."),
) -> None:
    """Write data/runs/<run_id>/report.md + report.json."""
    _not_implemented("P13")


@app.command()
def claims(
    run_id: str = typer.Argument(..., help="Run id to inspect."),
    verdict: str | None = typer.Option(None, "--verdict", help="Filter by verdict."),
    kind: str | None = typer.Option(None, "--kind", help="Filter by claim kind."),
) -> None:
    """Print a filtered claims table."""
    _not_implemented("P08")


@app.command()
def audit() -> None:
    """System audit (10 §3)."""
    _not_implemented("P24")


@app.command()
def eval() -> None:  # CLI command name is fixed by blueprint 12 §1
    """Run the gold-set evaluation (14)."""
    _not_implemented("P23")


@app.command()
def cost(
    since: str | None = typer.Option(None, "--since", help="Only include calls since DATE."),
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Token and cost summary from llm_calls."""
    from datetime import datetime

    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.providers import calllog
    from sots.storage import db as storage_db

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    since_dt: datetime | None = None
    if since is not None:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d")
        except ValueError:
            print(f"bad --since date {since!r}; use YYYY-MM-DD")
            raise typer.Exit(code=1) from None
    db_path = root / settings.paths.db_path
    if not db_path.is_file():
        print(f"no database yet at {db_path}")
        raise typer.Exit(code=1)
    conn = storage_db.connect(db_path)
    try:
        storage_db.migrate(conn)
        rows = calllog.summarize(conn, since_dt)
    finally:
        conn.close()
    if not rows:
        print("no LLM calls recorded")
        return
    print(f"{'task':<28}{'provider':<10}{'calls':>6}{'in_tok':>9}{'out_tok':>9}{'cost':>10}")
    total_cost = 0.0
    for row in rows:
        total_cost += row.cost
        print(
            f"{row.task:<28}{row.provider:<10}{row.calls:>6}"
            f"{row.input_tokens:>9}{row.output_tokens:>9}{row.cost:>10.4f}"
        )
    print(f"total cost: {total_cost:.4f}")


@app.command()
def tui() -> None:
    """Launch the Textual TUI."""
    _not_implemented("P22")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def write(ctx: typer.Context) -> None:
    """Free-form drafting (disabled: R-SCOPE-02)."""
    _ = ctx
    print("Writer is disabled (R-SCOPE-02)")
    raise typer.Exit(code=2)


@app.command()
def doctor(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """F17 health check (runs automatically before every act)."""
    import asyncio

    from rich.console import Console

    from sots.agents.failsafes.f17_doctor import format_report, run_doctor

    report = asyncio.run(run_doctor(root))
    Console().print(format_report(report))
    if report.failed:
        raise typer.Exit(code=1)


@app.command()
def stop(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """F16 kill switch: stop the current run immediately."""
    from sots.agents.failsafes.f16_killswitch import engage
    from sots.config import load_settings
    from sots.errors import ConfigError

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    path = engage(root / settings.paths.data_dir)
    print(f"stop requested: {path}")


@app.command()
def act(
    act_id: str = typer.Argument(..., help="Act to run: II, III, IV, V, or VI."),
    chapter_id: str = typer.Argument(..., help="Chapter id, e.g. ch03."),
) -> None:
    """Run a specific act for a chapter."""
    _not_implemented("P13")


@app.command()
def advance(chapter_id: str = typer.Argument(..., help="Chapter id, e.g. ch03.")) -> None:
    """Run the next eligible act for a chapter."""
    _not_implemented("P13")


@app.command()
def export(target: str = typer.Argument(..., help="Chapter id or 'all'.")) -> None:
    """Master output (19 §6)."""
    _not_implemented("P20")


@app.command()
def replay(run_id: str = typer.Argument(..., help="Run id to replay.")) -> None:
    """F18 deterministic replay of a run."""
    _not_implemented("P03")


@app.command()
def reason(
    scope: str = typer.Option("book", "--scope", help="Scope: book, phase, or chNN."),
    focus: str = typer.Option("both", "--focus", help="Focus: structure, ideas, or both."),
) -> None:
    """Recheck & Reason: re-examine structure and ideas (26)."""
    _not_implemented("P21A")


@app.command()
def revise(
    artifact_id: str = typer.Argument(..., help="Artifact id to revise."),
    note: str = typer.Option(..., "--note", help="Revision note (required)."),
) -> None:
    """Revise an artifact with a recorded note (R-MGE-04)."""
    _not_implemented("P20")


@app.command(name="master-audit")
def master_audit(
    sections: str | None = typer.Option(None, "--sections", help="Sections to audit."),
    book: bool = typer.Option(False, "--book", help="Audit the whole book."),
) -> None:
    """Master Audit battery over the book (28)."""
    _not_implemented("P24")


profile_app = typer.Typer(help="Author and book profile commands.", no_args_is_help=True)
app.add_typer(profile_app, name="profile")


@profile_app.command("interview")
def profile_interview(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Guided interview: writes profile/author.md and profile/book.md."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.profile.interview import run_interview

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    run_interview(root / settings.paths.profile_dir)


@profile_app.command("check")
def profile_check(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Validate the profile files and list what is missing."""
    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.profile.validate import check_profile

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    report = check_profile(root / settings.paths.profile_dir)
    if not report.findings:
        print("profile ok")
        return
    for finding in report.findings:
        print(f"[{finding.severity}] {finding.message}")
    if not report.ok:
        raise typer.Exit(code=1)


foundation_app = typer.Typer(help="Book Foundation commands (23).", no_args_is_help=True)
app.add_typer(foundation_app, name="foundation")


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


review_app = typer.Typer(help="Review queue stand-in (05 §3.4).", no_args_is_help=True)
app.add_typer(review_app, name="review")


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


expand_app = typer.Typer(help="Stage 11: Expansion Team.", no_args_is_help=True)
app.add_typer(expand_app, name="expand")


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


settings_app = typer.Typer(help="Settings and provider health.", no_args_is_help=True)
app.add_typer(settings_app, name="settings")


@settings_app.command("test-providers")
def settings_test_providers(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
) -> None:
    """Health-check each configured provider and fetcher."""
    import asyncio

    from sots.config import load_settings
    from sots.errors import ConfigError
    from sots.providers.router import build_registry

    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    registry = build_registry(settings)
    print(f"{'provider':<10}{'status':<16}detail")
    for name, provider in registry.items():
        health = asyncio.run(provider.health())
        status = "not configured"
        if provider.configured:
            status = "ok" if health.ok else "FAILED"
        print(f"{name:<10}{status:<16}{health.detail}")


chapter_app = typer.Typer(help="Per-chapter act state.", no_args_is_help=True)
app.add_typer(chapter_app, name="chapter")


@chapter_app.command("status")
def chapter_status(
    chapter_id: str | None = typer.Argument(None, help="Chapter id (default: all)."),
) -> None:
    """Show act, gates, and blocked reasons per chapter."""
    _not_implemented("P13")


style_guide_app = typer.Typer(help="Style Guide lifecycle (19 §1.2).", no_args_is_help=True)
app.add_typer(style_guide_app, name="style-guide")


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


revisions_app = typer.Typer(help="Revision history.", no_args_is_help=True)
app.add_typer(revisions_app, name="revisions")


@revisions_app.command("list")
def revisions_list(chapter_id: str = typer.Argument(..., help="Chapter id.")) -> None:
    """List revisions for a chapter."""
    _not_implemented("P15")


@revisions_app.command("diff")
def revisions_diff(
    rev_a: str = typer.Argument(..., help="First revision id."),
    rev_b: str = typer.Argument(..., help="Second revision id."),
) -> None:
    """Diff two revisions."""
    _not_implemented("P15")


hunks_app = typer.Typer(help="Hunk-by-hunk review (Pass B).", no_args_is_help=True)
app.add_typer(hunks_app, name="hunks")


@hunks_app.command("review")
def hunks_review(revision_id: str = typer.Argument(..., help="Revision id.")) -> None:
    """Terminal hunk-by-hunk accept/reject."""
    _not_implemented("P20")


audience_app = typer.Typer(help="Audience Lab (20).", no_args_is_help=True)
app.add_typer(audience_app, name="audience")


@audience_app.command("run")
def audience_run(revision_id: str = typer.Argument(..., help="Revision id.")) -> None:
    """Run the simulated-reader panel on a revision."""
    _not_implemented("P16")


@audience_app.command("import")
def audience_import(csv: Path = typer.Argument(..., help="CSV file to import.")) -> None:
    """Import audience data from CSV."""
    _not_implemented("P16")


@audience_app.command("questionnaire")
def audience_questionnaire() -> None:
    """Show the audience questionnaire."""
    _not_implemented("P16")


legal_app = typer.Typer(help="Legal Chamber (22).", no_args_is_help=True)
app.add_typer(legal_app, name="legal")


@legal_app.command("status")
def legal_status() -> None:
    """Show Legal Chamber status."""
    _not_implemented("P17")


@legal_app.command("issue")
def legal_issue(issue_id: str = typer.Argument(..., help="Issue id.")) -> None:
    """Show a legal issue memo."""
    _not_implemented("P17")


@legal_app.command("waive")
def legal_waive(
    issue_id: str = typer.Argument(..., help="Issue id."),
    attorney_confirmed: bool = typer.Option(
        False, "--attorney-confirmed", help="Required: a human attorney confirmed."
    ),
    reason_text: str = typer.Option(..., "--reason", help="Waiver reason (required)."),
) -> None:
    """Waive a legal issue (requires attorney confirmation + reason)."""
    _ = (attorney_confirmed, reason_text)
    _not_implemented("P17")


proposals_app = typer.Typer(help="Proposal Desk (18).", no_args_is_help=True)
app.add_typer(proposals_app, name="proposals")


@proposals_app.command("list")
def proposals_list() -> None:
    """List open proposals."""
    _not_implemented("P19")


@proposals_app.command("show")
def proposals_show(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Show a proposal card."""
    _not_implemented("P19")


@proposals_app.command("decide")
def proposals_decide(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Record a decision on a proposal."""
    _not_implemented("P19")


@proposals_app.command("archive")
def proposals_archive(
    proposal_id: str | None = typer.Argument(None, help="Proposal id."),
) -> None:
    """Archive a proposal."""
    _not_implemented("P19")


grader_app = typer.Typer(help="Quality gate grader (17).", no_args_is_help=True)
app.add_typer(grader_app, name="grader")


@grader_app.command("health")
def grader_health() -> None:
    """Grader calibration signals (17 §6)."""
    _not_implemented("P14")


learning_app = typer.Typer(help="Learning loop (20 §7).", no_args_is_help=True)
app.add_typer(learning_app, name="learning")


@learning_app.command("inbox")
def learning_inbox() -> None:
    """Show proposed prompt/threshold/persona/rubric changes."""
    _not_implemented("P21")


@learning_app.command("apply")
def learning_apply(change_id: str = typer.Argument(..., help="Change id.")) -> None:
    """Apply a proposed learning change."""
    _not_implemented("P21")


@learning_app.command("rollback")
def learning_rollback(change_id: str = typer.Argument(..., help="Change id.")) -> None:
    """Roll back an applied learning change."""
    _not_implemented("P21")


mge_app = typer.Typer(help="Master Grading Engine (27).", no_args_is_help=True)
app.add_typer(mge_app, name="mge")


@mge_app.command("stability")
def mge_stability() -> None:
    """Stability test: re-grade cached artifacts with the cache disabled."""
    _not_implemented("P14M")


voice_app = typer.Typer(help="Voice Lab (29).", no_args_is_help=True)
app.add_typer(voice_app, name="voice")


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


app.add_typer(vault_app, name="vault")
