"""Inbox / revisions / exports file helpers (P01 T01.034).

All writes are atomic: bytes go to a temp file in the same directory (flushed
and fsynced), then `os.replace` moves it over the target, so an interrupted
write never leaves a partial file behind.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

INBOX_DIR = "inbox"
REVISIONS_DIR = "revisions"
EXPORTS_DIR = "exports"


def ensure_dir(path: str | Path) -> Path:
    """Create a directory (parents included) and return it as a Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def inbox_path(root: str | Path, filename: str) -> Path:
    """Path for an immutable original under `<root>/inbox/`."""
    return Path(root) / INBOX_DIR / filename


def revision_path(root: str | Path, revision_id: str, filename: str = "text.md") -> Path:
    """Path for revision text under `<root>/revisions/<revision_id>/`."""
    return Path(root) / REVISIONS_DIR / revision_id / filename


def export_path(root: str | Path, filename: str) -> Path:
    """Path for a deliverable under `<root>/exports/`."""
    return Path(root) / EXPORTS_DIR / filename


def atomic_write_bytes(path: str | Path, data: bytes) -> Path:
    """Write bytes atomically via temp file + rename; return the target path."""
    target = Path(path)
    ensure_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    return target


def atomic_write_text(path: str | Path, text: str, encoding: str = "utf-8") -> Path:
    """Write text atomically via temp file + rename; return the target path."""
    return atomic_write_bytes(path, text.encode(encoding))


def read_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def read_text(path: str | Path, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)
