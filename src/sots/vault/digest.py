"""Author-notes digest: margin notes collected into one navigable note (OI-42).

The digest reads `## Author notes` sections back out of the vault so thoughts
written in Obsidian become browsable context instead of scattered text. It
never modifies the source notes, and placeholder-only sections are skipped.
"""

from __future__ import annotations

from pathlib import Path

from sots.models.vault import VaultAuthorNote, VaultNote
from sots.vault import paths
from sots.vault.writer import (
    AUTHOR_PLACEHOLDER,
    DEFAULT_AUTHOR_HEADING,
    GENERATED_START,
    WriteOutcome,
    extract_author_section,
    write_note,
)

MAX_ENTRY_CHARS = 2000


def _is_empty_author_text(text: str, author_heading: str) -> bool:
    """True when a section holds nothing but the heading and/or placeholder."""
    body = text
    if body.startswith(author_heading):
        body = body[len(author_heading) :]
    return body.strip() in ("", AUTHOR_PLACEHOLDER)


def collect_author_notes(
    vault_root: str | Path,
    author_heading: str = DEFAULT_AUTHOR_HEADING,
) -> list[VaultAuthorNote]:
    """Every non-empty author section, sorted by note path (deterministic).

    Only managed notes (files carrying the generated marker) are scanned:
    scaffolding like README.md and the author's own freeform notes are notes
    in their own right, not margin sections to quote.
    """
    root = Path(vault_root)
    digest_name = Path(paths.AUTHOR_DIGEST_NOTE).name
    entries: list[VaultAuthorNote] = []
    for note_path in sorted(root.rglob("*.md")):
        if note_path.name == digest_name:
            continue
        try:
            existing = note_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if GENERATED_START not in existing:
            continue
        section = extract_author_section(existing, author_heading)
        if not section or _is_empty_author_text(section, author_heading):
            continue
        entries.append(
            VaultAuthorNote(
                rel_path=note_path.relative_to(root).as_posix(), text=section.rstrip()
            )
        )
    return entries


def build_digest_note(entries: list[VaultAuthorNote]) -> VaultNote:
    """Digest note quoting each author section under a backlink heading."""
    lines = ["# Author Notes Digest", ""]
    lines.append("> Your margin notes, collected by `sots vault digest`.")
    lines.append("")
    if not entries:
        lines.append("_No author notes written yet._")
    for entry in entries:
        stem = entry.rel_path[:-3] if entry.rel_path.endswith(".md") else entry.rel_path
        lines.append(f"## [[{stem}]]")
        lines.append("")
        text = entry.text
        if len(text) > MAX_ENTRY_CHARS:
            text = text[:MAX_ENTRY_CHARS].rstrip() + "\n…(truncated)"
        lines.append(text)
        lines.append("")
    return VaultNote(
        rel_path=paths.AUTHOR_DIGEST_NOTE,
        frontmatter={"tags": ["moc", "author"]},
        generated_body="\n".join(lines).rstrip() + "\n",
    )


def refresh_digest(
    vault_root: str | Path,
    author_heading: str = DEFAULT_AUTHOR_HEADING,
) -> WriteOutcome:
    """Rebuild the digest note from current author sections (F07)."""
    root = Path(vault_root)
    return write_note(root, build_digest_note(collect_author_notes(root, author_heading)))
