"""LLM response cache over the `cache` table (P02 T02.014, R-LLM-05).

Key = sha256(provider, model, prompt_id, version, rendered_input, temperature).
Identical calls are served from the cache and never pay twice; `--no-cache`
bypasses both read and write. Entries never expire (fetch TTLs do not apply).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sots.models.cache import CacheEntry
from sots.storage import repo as storage_repo
from sots.storage.db import Connection


def cache_key(
    provider: str,
    model: str,
    prompt_id: str,
    prompt_version: int,
    rendered_input: str,
    temperature: float,
) -> str:
    """T02.014 cache key: sha256 over the canonical call fields."""
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "rendered_input": rendered_input,
            "temperature": temperature,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_get(conn: Connection, key: str) -> str | None:
    """Cached validated-JSON value, or None on miss/expiry (never raises)."""
    entry = storage_repo.get_cache_entry(conn, key)
    if entry is None:
        return None
    if entry.expires_at is not None:
        expires = entry.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= datetime.now(UTC):
            return None
    return entry.value


def cache_put(conn: Connection, key: str, value: str) -> None:
    """Store a validated result (upsert on key); entries never expire."""
    storage_repo.save_cache_entry(
        conn, CacheEntry(key=key, value=value, created_at=datetime.now(UTC), expires_at=None)
    )


def cache_stats(conn: Connection) -> dict[str, Any]:
    """Row count for diagnostics (used by `sots cost` / doctor later)."""
    return {"entries": storage_repo.count_cache_entries(conn)}
