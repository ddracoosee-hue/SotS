"""Vault sync: `profile/` -> managed notes, idempotent with staleness (OI-42)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from sots.models.run import ChapterState
from sots.models.vault import (
    VaultCounts,
    VaultFoundation,
    VaultNote,
    VaultStaleFile,
    VaultSyncState,
)
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo
from sots.storage.files import atomic_write_text, ensure_dir
from sots.vault import digest as vault_digest
from sots.vault import notes, paths, readme
from sots.vault.dashboard import build_dashboard_note, build_reading_order_note
from sots.vault.writer import (
    DEFAULT_AUTHOR_HEADING,
    WriteOutcome,
    write_note,
    write_static,
)

logger = logging.getLogger(__name__)

OBSIDIAN_APP_JSON_CONTENT = json.dumps(
    {
        "promptDelete": False,
        "newLinkFormat": "shortest",
        "useMarkdownLinks": False,
        "showLineNumber": True,
    },
    indent=2,
) + "\n"


def file_hash(path: str | Path) -> str | None:
    """SHA-256 hex of a file, or None when it does not exist."""
    candidate = Path(path)
    if not candidate.is_file():
        return None
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    """Parse a YAML mapping; missing files yield {} (partial profiles sync)."""
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_brief_header(brief_path: str | Path) -> str:
    """First non-empty line of a chapter brief ("" when missing/unreadable)."""
    candidate = Path(brief_path)
    if not candidate.is_file():
        return ""
    try:
        text = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.strip():
            return " ".join(line.split())
    return ""


def discover_chapters(profile_dir: str | Path) -> list[str]:
    """Chapter ids from briefs + messages + architecture, sorted (R-FOUND-03)."""
    root = Path(profile_dir)
    found: set[str] = set()
    chapters_dir = root / "chapters"
    if chapters_dir.is_dir():
        for brief in chapters_dir.glob("ch??_brief.md"):
            found.add(brief.name[:4])
    messages = load_yaml_mapping(root / "messages.yaml")
    chapters = messages.get("chapters") or {}
    if isinstance(chapters, dict):
        found.update(str(k) for k in chapters if paths.is_chapter_id(str(k)))
    arch = load_yaml_mapping(root / "book_architecture.yaml")
    order = arch.get("reading_order") or []
    found.update(str(c) for c in order if paths.is_chapter_id(str(c)))
    return sorted(found)


def load_chapter_states(db_path: str | Path | None) -> dict[str, ChapterState]:
    """Chapter pipeline states from SQLite; {} when the DB is absent/unreadable.

    Reads through `storage.repo` (the only SQL module); the vault degrades to
    "pipeline has not run" notes instead of failing the sync.
    """
    if db_path is None:
        return {}
    candidate = Path(db_path)
    if not candidate.is_file():
        return {}
    try:
        conn = storage_db.connect(candidate)
        try:
            states = storage_repo.list_chapter_states(conn)
        finally:
            conn.close()
    except Exception as exc:  # mirror degrades, never fails the sync
        logger.warning("vault chapter states unavailable: %s", exc)
        return {}
    return {state.chapter_id: state for state in states}


def load_foundation(
    profile_dir: str | Path, db_path: str | Path | None = None
) -> VaultFoundation:
    """Read the draft foundation files into one snapshot for the builders."""
    root = Path(profile_dir)
    messages = load_yaml_mapping(root / "messages.yaml")
    anchors_doc = load_yaml_mapping(root / "anchors.yaml")
    arch = load_yaml_mapping(root / "book_architecture.yaml")
    chapter_ids = discover_chapters(root)
    chapter_messages: dict[str, list[dict]] = {}
    raw_chapters = messages.get("chapters") or {}
    if isinstance(raw_chapters, dict):
        for key, value in raw_chapters.items():
            if isinstance(value, list):
                chapter_messages[str(key)] = [dict(m) for m in value if isinstance(m, dict)]
    anchors = anchors_doc.get("anchors") or []
    brief_headers = {
        cid: read_brief_header(root / "chapters" / f"{cid}_brief.md") for cid in chapter_ids
    }
    hard = arch.get("hard_dependencies") or []
    return VaultFoundation(
        chapter_ids=chapter_ids,
        book_messages=[dict(m) for m in (messages.get("book") or []) if isinstance(m, dict)],
        chapter_messages=chapter_messages,
        anchors=[dict(a) for a in anchors if isinstance(a, dict)],
        reading_order=[str(c) for c in (arch.get("reading_order") or [])],
        phases=[dict(p) for p in (arch.get("phases") or []) if isinstance(p, dict)],
        arc=[dict(e) for e in (arch.get("arc") or []) if isinstance(e, dict)],
        motif_serials=[dict(s) for s in (arch.get("motif_serials") or []) if isinstance(s, dict)],
        brief_headers=brief_headers,
        architecture_status=str(arch.get("status", "unknown")),
        hard_dependencies=[str(d) for d in hard],
        chapter_states=load_chapter_states(db_path),
    )


def foundation_files(profile_dir: str | Path) -> list[Path]:
    """Every foundation input mirrored into the vault (existing files only)."""
    root = Path(profile_dir)
    files = [root / name for name in paths.FOUNDATION_FILES]
    chapters_dir = root / "chapters"
    if chapters_dir.is_dir():
        files.extend(sorted(chapters_dir.glob("ch??_brief.md")))
    return [p for p in files if p.is_file()]


def foundation_hashes(profile_dir: str | Path) -> dict[str, str]:
    """POSIX-relative path -> sha256 for each mirrored foundation file."""
    root = Path(profile_dir)
    hashes: dict[str, str] = {}
    for path in foundation_files(root):
        digest = file_hash(path)
        if digest is not None:
            hashes[path.relative_to(root).as_posix()] = digest
    return hashes


def collect_notes(foundation: VaultFoundation) -> list[VaultNote]:
    """Build every managed note: index, dashboard, chapters, anchors, messages."""
    all_notes: list[VaultNote] = [
        notes.build_book_index(foundation),
        build_dashboard_note(foundation),
    ]
    for chapter_id in foundation.chapter_ids:
        all_notes.append(notes.build_chapter_note(foundation, chapter_id))
    for anchor in foundation.anchors:
        if anchor.get("id"):
            all_notes.append(notes.build_anchor_note(dict(anchor)))
    for message in foundation.book_messages:
        mid = str(message.get("id", ""))
        if mid:
            all_notes.append(
                notes.build_message_note(
                    mid,
                    str(message.get("statement", "")),
                    message.get("priority", "?"),
                    "book",
                    None,
                    foundation,
                )
            )
    for chapter_id, messages in foundation.chapter_messages.items():
        for message in messages:
            mid = str(message.get("id", ""))
            if mid:
                all_notes.append(
                    notes.build_message_note(
                        mid,
                        str(message.get("statement", "")),
                        message.get("priority", "?"),
                        "chapter",
                        str(chapter_id),
                        foundation,
                    )
                )
    for serial in foundation.motif_serials:
        motif = str(serial.get("motif", ""))
        plan = serial.get("plan") or {}
        if motif and isinstance(plan, dict):
            all_notes.append(notes.build_motif_note(motif, dict(plan)))
    all_notes.append(build_reading_order_note(foundation))
    return all_notes


def _tally(counts: dict[str, int], outcome: WriteOutcome) -> None:
    counts[outcome] += 1


def init_vault(vault_root: str | Path) -> VaultCounts:
    """Create vault scaffolding (subdirs, README, Obsidian config); idempotent."""
    root = Path(vault_root)
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for subdir in paths.vault_subdirs():
        target = root / subdir
        if target.is_dir():
            continue
        ensure_dir(target)
        counts["created"] += 1
    _tally(counts, write_static(root, paths.VAULT_README, readme.build_vault_readme()))
    _tally(counts, write_static(root, paths.OBSIDIAN_APP_JSON, OBSIDIAN_APP_JSON_CONTENT))
    return VaultCounts(**counts)


def sync_foundation(
    profile_dir: str | Path,
    vault_root: str | Path,
    author_heading: str = DEFAULT_AUTHOR_HEADING,
    db_path: str | Path | None = None,
) -> VaultCounts:
    """Rebuild managed notes from `profile/`; preserve author sections (F07)."""
    root = Path(vault_root)
    init_vault(root)
    foundation = load_foundation(profile_dir, db_path)
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for note in collect_notes(foundation):
        _tally(counts, write_note(root, note, author_heading))
    _tally(counts, vault_digest.refresh_digest(root, author_heading))
    state = VaultSyncState(
        vault_version=paths.VAULT_VERSION,
        foundation_hashes=foundation_hashes(profile_dir),
        synced_at=datetime.now(UTC),
    )
    atomic_write_text(
        root / paths.SYNC_STATE_FILE,
        yaml.safe_dump(state.model_dump(mode="json"), sort_keys=True),
    )
    return VaultCounts(**counts)


def read_sync_state(vault_root: str | Path) -> VaultSyncState:
    """Last sync state, or a blank one when the vault never synced."""
    candidate = Path(vault_root) / paths.SYNC_STATE_FILE
    if not candidate.is_file():
        return VaultSyncState()
    try:
        data = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return VaultSyncState()
    if not isinstance(data, dict):
        return VaultSyncState()
    try:
        return VaultSyncState.model_validate(data)
    except ValueError:
        return VaultSyncState()


def vault_status(profile_dir: str | Path, vault_root: str | Path) -> list[VaultStaleFile]:
    """Foundation files changed, added, or removed since the last sync."""
    expected = read_sync_state(vault_root).foundation_hashes
    current = foundation_hashes(profile_dir)
    stale: list[VaultStaleFile] = []
    for path in sorted(set(expected) | set(current)):
        old, new = expected.get(path), current.get(path)
        if old != new:
            stale.append(VaultStaleFile(path=path, expected_hash=old, current_hash=new))
    return stale
