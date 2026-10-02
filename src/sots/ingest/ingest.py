"""Stage 1 ingest pipeline (P04 T04.012-T04.013, 05 Stage 1).

sha256 → duplicate check → byte-identical inbox copy → canonical .txt →
Document row. Pasted text is staged as `paste_<ts>.md` first, then ingested
as usual.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.ingest.loader import extract_text
from sots.ingest.normalize import normalize_text
from sots.models.document import Document
from sots.models.ids import new_id
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


class IngestOutcome(BaseModel):
    """What one ingest produced (a reuse carries `duplicate_of`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: Document
    duplicate_of: str | None
    warnings: list[str]


def file_sha256(path: str | Path) -> str:
    """sha256 of the raw file bytes (05 Stage 1, step 1)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_by_sha256(conn: Connection, digest: str) -> Document | None:
    """The ingested document with this hash, if any (duplicate check)."""
    rows = storage_repo.list_documents(conn, sha256=digest)
    return rows[0] if rows else None


def ingest_file(
    source: str | Path,
    *,
    conn: Connection,
    inbox_dir: str | Path,
    title: str | None = None,
    chapter_id: str | None = None,
    allow_duplicate: bool = False,
) -> IngestOutcome:
    """Ingest one file (05 Stage 1); same-hash files reuse unless allowed."""
    src = Path(source)
    digest = file_sha256(src)
    existing = find_by_sha256(conn, digest)
    if existing is not None and not allow_duplicate:
        return IngestOutcome(document=existing, duplicate_of=existing.id, warnings=[])
    extracted = extract_text(src)
    canonical = normalize_text(extracted.text)
    doc_id = new_id("doc")
    inbox = Path(inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    raw_copy = inbox / f"{doc_id}{src.suffix.lower()}"
    shutil.copyfile(src, raw_copy)
    (inbox / f"{doc_id}.txt").write_text(canonical, encoding="utf-8", newline="")
    document = Document(
        id=doc_id,
        source_path=str(src),
        inbox_path=str(raw_copy),
        sha256=digest,
        title=title or src.stem,
        chapter_id=chapter_id,
        char_count=len(canonical),
        word_count=len(canonical.split()),
        ingested_at=datetime.now(UTC),
    )
    storage_repo.save_document(conn, document)
    return IngestOutcome(document=document, duplicate_of=None, warnings=extracted.warnings)


def ingest_paste(
    text: str,
    *,
    conn: Connection,
    inbox_dir: str | Path,
    title: str | None = None,
    chapter_id: str | None = None,
) -> IngestOutcome:
    """Ingest pasted text via a staged `paste_<ts>.md` file (05 Stage 1)."""
    inbox = Path(inbox_dir)
    inbox.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    staged = inbox / f"paste_{stamp}.md"
    counter = 2
    while staged.exists():
        staged = inbox / f"paste_{stamp}_{counter}.md"
        counter += 1
    staged.write_text(text, encoding="utf-8", newline="")
    return ingest_file(
        staged, conn=conn, inbox_dir=inbox, title=title or staged.stem,
        chapter_id=chapter_id,
    )
