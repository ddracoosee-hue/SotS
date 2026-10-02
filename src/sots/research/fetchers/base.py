"""Fetcher protocol + shared guards (P07, 06 §3.2).

Every fetcher runs behind F02 (retry), F03 (breaker), F13 (injection strip),
F14 (rate limit + robots + UA), and F15 (size caps). Dependencies arrive via
`FetcherDeps` so tests can substitute freely.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from sots.agents.failsafes.f02_retry import with_retry
from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f13_injection import strip_injections
from sots.agents.failsafes.f14_politeness import PolitenessGate
from sots.agents.failsafes.f15_size import cap_text
from sots.config import Settings
from sots.models.evidence import FetchedDoc

logger = logging.getLogger(__name__)

#: Cap on extracted text per document (F15).
MAX_FETCHED_CHARS = 500_000


class Fetcher(Protocol):
    """One research source (06 §3.2)."""

    name: str

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Structured search for `query` (direct API lookups)."""
        ...

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """Fetch one URL (None when missing or unsupported)."""
        ...


@dataclass
class FetcherDeps:
    """Shared fetcher dependencies (one breaker per fetcher instance)."""

    settings: Settings
    cache_dir: Path
    gate: PolitenessGate
    breaker: CircuitBreaker


def doc_hash(text: str) -> str:
    """Content hash for a fetched text (evidence + cache identity)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_text(text: str, patterns: list[str]) -> str:
    """F13 strip + F15 cap (both logged, never silent)."""
    stripped, count = strip_injections(text, patterns)
    if count:
        logger.info("F13_INJECTION_STRIPPED patterns=%d", count)
    capped, note = cap_text(stripped, MAX_FETCHED_CHARS, "fetched text")
    if note is not None:
        logger.warning("fetched text trimmed: %s", note)
    return capped


async def fetch_json(
    url: str,
    *,
    deps: FetcherDeps,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET JSON behind the rate limit, breaker, and retry (no robots: APIs)."""
    await deps.gate.acquire(url)
    merged = {"User-Agent": deps.gate.user_agent, "Accept": "application/json"}
    if headers:
        merged.update(headers)

    async def _get() -> Any:
        async with httpx.AsyncClient(
            timeout=deps.settings.fetch.timeout_s, headers=merged
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    return await deps.breaker.call(lambda: with_retry(_get))


async def fetch_text(
    url: str,
    *,
    deps: FetcherDeps,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> str:
    """GET text behind the rate limit, breaker, and retry (no robots: APIs)."""
    await deps.gate.acquire(url)
    merged = {"User-Agent": deps.gate.user_agent}
    if headers:
        merged.update(headers)

    async def _get() -> str:
        async with httpx.AsyncClient(
            timeout=deps.settings.fetch.timeout_s, headers=merged
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.text

    return await deps.breaker.call(lambda: with_retry(_get))
