"""Fetch cache: `<url-hash>.txt` + `<url-hash>.json` (P07, 06 §3.2).

The `.txt` holds the full extracted text (what citation checks verify
against); the `.json` holds the FetchedDoc metadata in the tool-compatible
format. Entries older than `settings.cache.fetch_ttl_days` refetch.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from sots.models.evidence import FetchedDoc
from sots.storage.files import atomic_write_bytes, atomic_write_text, ensure_dir


def url_hash(url: str) -> str:
    """Cache identity for a URL (06 §3.2)."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def cache_paths(cache_dir: str | Path, url: str) -> tuple[Path, Path]:
    """The (text, meta) paths for a URL."""
    digest = url_hash(url)
    root = Path(cache_dir)
    return root / f"{digest}.txt", root / f"{digest}.json"


def read_cached(
    cache_dir: str | Path, url: str, *, ttl_days: int
) -> FetchedDoc | None:
    """A fresh cached doc, or None when missing/stale/incomplete."""
    text_path, meta_path = cache_paths(cache_dir, url)
    if not text_path.is_file() or not meta_path.is_file():
        return None
    age_days = (time.time() - meta_path.stat().st_mtime) / 86400
    if age_days > ttl_days:
        return None
    try:
        return FetchedDoc.model_validate_json(meta_path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def write_cached(cache_dir: str | Path, doc: FetchedDoc) -> tuple[Path, Path]:
    """Store text + metadata atomically; returns the paths."""
    text_path, meta_path = cache_paths(cache_dir, doc.url)
    ensure_dir(text_path.parent)
    atomic_write_bytes(text_path, doc.text.encode("utf-8"))
    atomic_write_text(meta_path, doc.model_dump_json())
    return text_path, meta_path
