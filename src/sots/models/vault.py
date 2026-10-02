"""Obsidian-vault mirror models (author-approved addition, OI-42).

The vault is a human-readable, wikilinked Markdown mirror of the Book
Foundation (`profile/`). SQLite stays the system of record for runs;
the vault keeps chapter context and whole-book threads (anchors, motifs,
messages, reading order) navigable across chapters in Obsidian.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from sots.models.run import ChapterState


class VaultNote(BaseModel):
    """One managed Markdown note inside the vault (path relative to vault root)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rel_path: str
    frontmatter: dict
    generated_body: str


class VaultCounts(BaseModel):
    """Note write outcomes for one sync (F07-style idempotency accounting)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    created: int = 0
    updated: int = 0
    unchanged: int = 0


class VaultSyncState(BaseModel):
    """What foundation revision the vault currently mirrors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    vault_version: int = 1
    foundation_hashes: dict[str, str] = {}
    synced_at: datetime | None = None


class VaultStaleFile(BaseModel):
    """One foundation file whose hash differs from the last sync."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    expected_hash: str | None
    current_hash: str | None


class VaultFoundation(BaseModel):
    """Foundation snapshot crossing into the note builders (R-CODE-04).

    Lists/dicts mirror the `profile/` YAML shapes; P04A's typed loader will
    replace this with structured briefs when it lands.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_ids: list[str] = []
    book_messages: list[dict] = []
    chapter_messages: dict[str, list[dict]] = {}
    anchors: list[dict] = []
    reading_order: list[str] = []
    phases: list[dict] = []
    arc: list[dict] = []
    motif_serials: list[dict] = []
    brief_headers: dict[str, str] = {}
    architecture_status: str = "unknown"
    hard_dependencies: list[str] = []
    chapter_states: dict[str, ChapterState] = {}


class VaultAuthorNote(BaseModel):
    """One note's author-written section, collected for the digest (R-CODE-04)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rel_path: str
    text: str
