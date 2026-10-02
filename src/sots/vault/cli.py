"""`sots vault` commands: Obsidian-vault mirror of the foundation (OI-42)."""

# ruff: noqa: B008 - typer.Option in defaults is the idiomatic Typer pattern.

from __future__ import annotations

from pathlib import Path

import typer

from sots.config import Settings, load_settings
from sots.errors import ConfigError
from sots.vault.digest import refresh_digest
from sots.vault.sync import init_vault, sync_foundation, vault_status

vault_app = typer.Typer(
    help="Obsidian vault mirror: chapter context + whole-book threads.",
    no_args_is_help=True,
)


def _resolve_dirs(
    root: Path, profile: str | None, vault: str | None
) -> tuple[Settings, Path, Path]:
    """Settings plus profile/vault dirs (options win, else settings.yaml)."""
    try:
        settings = load_settings(root / "config")
    except ConfigError as exc:
        print(f"cannot load settings: {exc}")
        raise typer.Exit(code=1) from exc
    profile_dir = root / (profile or settings.paths.profile_dir)
    vault_dir = root / (vault or settings.paths.vault_dir)
    return settings, profile_dir, vault_dir


@vault_app.command("init")
def vault_init(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
    vault: str | None = typer.Option(None, "--vault", help="Vault dir override."),
) -> None:
    """Create the vault scaffolding (idempotent; never overwrites notes)."""
    _, _, vault_dir = _resolve_dirs(root, None, vault)
    counts = init_vault(vault_dir)
    print(
        f"vault ready at {vault_dir} "
        f"(created={counts.created} unchanged={counts.unchanged})"
    )


@vault_app.command("sync")
def vault_sync(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
    profile: str | None = typer.Option(None, "--profile", help="Profile dir override."),
    vault: str | None = typer.Option(None, "--vault", help="Vault dir override."),
) -> None:
    """Rebuild managed notes from profile/; author sections are preserved."""
    settings, profile_dir, vault_dir = _resolve_dirs(root, profile, vault)
    if not profile_dir.is_dir():
        print(f"profile dir not found: {profile_dir}")
        raise typer.Exit(code=1)
    counts = sync_foundation(
        profile_dir,
        vault_dir,
        settings.vault.author_notes_heading,
        root / settings.paths.db_path,
    )
    print(
        f"synced {vault_dir} from {profile_dir} "
        f"(created={counts.created} updated={counts.updated} "
        f"unchanged={counts.unchanged})"
    )


@vault_app.command("status")
def vault_state(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
    profile: str | None = typer.Option(None, "--profile", help="Profile dir override."),
    vault: str | None = typer.Option(None, "--vault", help="Vault dir override."),
) -> None:
    """Show foundation files changed since the last vault sync."""
    _, profile_dir, vault_dir = _resolve_dirs(root, profile, vault)
    stale = vault_status(profile_dir, vault_dir)
    if not stale:
        print(f"vault {vault_dir} is up to date")
        return
    print(f"vault {vault_dir} is stale ({len(stale)} file(s)):")
    for item in stale:
        print(f"  {item.path}")


@vault_app.command("digest")
def vault_digest_cmd(
    root: Path = typer.Option(Path("."), "--root", help="Project root."),
    vault: str | None = typer.Option(None, "--vault", help="Vault dir override."),
) -> None:
    """Collect author margin notes into the Author Notes Digest note."""
    settings, _, vault_dir = _resolve_dirs(root, None, vault)
    outcome = refresh_digest(vault_dir, settings.vault.author_notes_heading)
    print(f"digest {outcome}: {vault_dir / 'Author Notes Digest.md'}")
