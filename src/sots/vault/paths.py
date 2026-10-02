"""Vault layout, note paths, and stable chapter titles (OI-42)."""

from __future__ import annotations

import re
from pathlib import Path

VAULT_VERSION = 1

CHAPTERS_DIR = "Chapters"
ANCHORS_DIR = "Anchors"
MESSAGES_DIR = "Messages"
MOTIFS_DIR = "Motifs"
ARCH_DIR = "Architecture"
OBSIDIAN_DIR = ".obsidian"

BOOK_INDEX_NOTE = "Book Index.md"
BOOK_DASHBOARD_NOTE = "Book Dashboard.md"
AUTHOR_DIGEST_NOTE = "Author Notes Digest.md"
VAULT_README = "README.md"
SYNC_STATE_FILE = ".sots-sync.yaml"
OBSIDIAN_APP_JSON = ".obsidian/app.json"

CHAPTER_NOTE_RE = re.compile(r"^ch(\d{2})$")
ANCHOR_ID_RE = re.compile(r"^(ch\d{2})\.([AP]\d+)$")
_NON_SLUG = re.compile(r"[^a-z0-9]+")

# Canonical short titles. Sources: brief headers where present (ch01, ch02, ch04,
# ch05, ch12), else the chapter label used in profile/messages.yaml comments.
# Provisional like the rest of the draft foundation; filenames stay stable even
# if display titles are refined later (renames would break [[wikilinks]]).
CHAPTER_TITLES: dict[str, str] = {
    "ch01": "The Modern Day",
    "ch02": "Sense of Self",
    "ch03": "Consciousness",
    "ch04": "The Danger",
    "ch05": "Balance",
    "ch06": "Collective Action",
    "ch07": "The Easy Yoke",
    "ch08": "The Re-Authored Life",
    "ch09": "Practical Mastery",
    "ch10": "The Defiant Spirit",
    "ch11": "Architecture of Shame",
    "ch12": "The Drum Major Instinct",
}

# Foundation inputs mirrored into the vault (relative to profile_dir).
FOUNDATION_FILES: tuple[str, ...] = (
    "book.md",
    "author.md",
    "messages.yaml",
    "anchors.yaml",
    "book_architecture.yaml",
    "style_guide_seed.yaml",
)


def slugify(text: str) -> str:
    """Lowercase slug for motif filenames: `Provocation spiral` -> `provocation-spiral`."""
    slug = _NON_SLUG.sub("-", text.strip().lower()).strip("-")
    return slug or "untitled"


def chapter_title(chapter_id: str) -> str:
    """Short display title for a chapter id (falls back to the id itself)."""
    return CHAPTER_TITLES.get(chapter_id, chapter_id)


def chapter_note_rel_path(chapter_id: str) -> str:
    """Vault-relative note path, e.g. `Chapters/ch01 - The Modern Day.md`."""
    return f"{CHAPTERS_DIR}/{chapter_id} - {chapter_title(chapter_id)}.md"


def chapter_stem(chapter_id: str) -> str:
    """Wikilink target stem without `.md` (Obsidian resolves it vault-wide)."""
    return f"{CHAPTERS_DIR}/{chapter_id} - {chapter_title(chapter_id)}"


def anchor_note_rel_path(anchor_id: str) -> str:
    """Vault-relative note path, e.g. `Anchors/ch01.A01.md`."""
    safe = anchor_id.replace("/", "-")
    return f"{ANCHORS_DIR}/{safe}.md"


def anchor_stem(anchor_id: str) -> str:
    """Wikilink target stem for an anchor note."""
    safe = anchor_id.replace("/", "-")
    return f"{ANCHORS_DIR}/{safe}"


def message_note_rel_path(message_id: str) -> str:
    """Vault-relative note path, e.g. `Messages/M1.md` or `Messages/C1.1.md`."""
    safe = message_id.replace("/", "-")
    return f"{MESSAGES_DIR}/{safe}.md"


def message_stem(message_id: str) -> str:
    """Wikilink target stem for a message note."""
    safe = message_id.replace("/", "-")
    return f"{MESSAGES_DIR}/{safe}"


def motif_note_rel_path(motif: str) -> str:
    """Vault-relative note path, e.g. `Motifs/provocation-spiral.md`."""
    return f"{MOTIFS_DIR}/{slugify(motif)}.md"


def motif_stem(motif: str) -> str:
    """Wikilink target stem for a motif note."""
    return f"{MOTIFS_DIR}/{slugify(motif)}"


def wikilink(stem: str, label: str | None = None) -> str:
    """An Obsidian `[[link]]`, with `|label` only when it differs from the stem."""
    if label is None or label == stem:
        return f"[[{stem}]]"
    return f"[[{stem}|{label}]]"


def chapter_link(chapter_id: str) -> str:
    """Wikilink to a chapter note, labeled `chNN · Title`."""
    return wikilink(chapter_stem(chapter_id), f"{chapter_id} · {chapter_title(chapter_id)}")


def chapter_id_from_anchor(anchor_id: str) -> str | None:
    """Owning chapter of an anchor id (`ch03.A06` -> `ch03`), else None."""
    match = ANCHOR_ID_RE.match(anchor_id)
    return match.group(1) if match else None


def is_chapter_id(value: str) -> bool:
    """True for `ch01`-`ch99` ids (R-FOUND-03 keeps ch01-ch12 forever)."""
    return CHAPTER_NOTE_RE.match(value) is not None


def vault_subdirs() -> tuple[str, ...]:
    """Managed note folders created by `sots vault init`."""
    return (CHAPTERS_DIR, ANCHORS_DIR, MESSAGES_DIR, MOTIFS_DIR, ARCH_DIR)


def resolve(vault_root: str | Path, rel_path: str) -> Path:
    """Absolute path of a vault-relative note path."""
    return Path(vault_root) / rel_path
