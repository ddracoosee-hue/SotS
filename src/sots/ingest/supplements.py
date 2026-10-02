"""supplements/ reference index (P04 T04.015, 05 Stage 1).

The same loaders as ingest; text (normalized) + file-bytes sha256 land in
`supplement_docs`, where the P07 supplements fetcher reads them. Re-running
only re-indexes changed files.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.ingest.loader import extract_text
from sots.ingest.normalize import normalize_text
from sots.models.document import SupplementDoc
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

logger = logging.getLogger(__name__)


class SupplementReport(BaseModel):
    """Indexing outcome (paths relative to supplements/)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    indexed: int
    unchanged: int
    skipped: dict[str, str]


def _visible_files(root: Path) -> list[Path]:
    """All files except dotfiles/dot-directories, in sorted order."""
    found = [
        path for path in root.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    return sorted(found)


def index_supplements(supplements_dir: str | Path, conn: Connection) -> SupplementReport:
    """(Re-)index supplements/; returns counts + skip reasons (T04.015)."""
    root = Path(supplements_dir)
    if not root.is_dir():
        return SupplementReport(indexed=0, unchanged=0, skipped={})
    indexed = 0
    unchanged = 0
    skipped: dict[str, str] = {}
    for path in _visible_files(root):
        rel = str(path.relative_to(root))
        try:
            extracted = extract_text(path)
        except ValueError:
            skipped[rel] = "unsupported format"
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        existing = storage_repo.get_supplement_doc(conn, rel)
        if existing is not None and existing.sha256 == digest:
            unchanged += 1
            continue
        for warning in extracted.warnings:
            logger.warning("supplement %s: %s", rel, warning)
        storage_repo.save_supplement_doc(
            conn,
            SupplementDoc(
                path=rel,
                sha256=digest,
                text=normalize_text(extracted.text),
                indexed_at=datetime.now(UTC),
            ),
        )
        indexed += 1
    return SupplementReport(indexed=indexed, unchanged=unchanged, skipped=skipped)
