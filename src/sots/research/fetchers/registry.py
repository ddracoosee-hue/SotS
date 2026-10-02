"""Fetcher registry: key-gated construction + status (P07 T07.020).

`build_fetchers` wires every fetcher with shared settings/cache/gate and a
private circuit breaker; `fetcher_status` reports which are live and why the
rest are disabled (for the CLI/doctor and the research report).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.failsafes.f14_politeness import PolitenessGate
from sots.config import Settings
from sots.research.fetchers.base import Fetcher, FetcherDeps
from sots.research.fetchers.courtlistener import CourtlistenerFetcher
from sots.research.fetchers.crossref import CrossrefFetcher
from sots.research.fetchers.google_factcheck import GoogleFactcheckFetcher
from sots.research.fetchers.musicbrainz import MusicbrainzFetcher
from sots.research.fetchers.openalex import OpenAlexFetcher
from sots.research.fetchers.openlibrary import OpenlibraryFetcher
from sots.research.fetchers.supplements import SupplementsFetcher
from sots.research.fetchers.tmdb import TmdbFetcher
from sots.research.fetchers.web import WebFetcher
from sots.research.fetchers.wikipedia import WikipediaFetcher
from sots.storage.db import Connection


class FetcherStatus(BaseModel):
    """One fetcher's availability (06 §3.2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    enabled: bool
    reason: str


def _deps(
    settings: Settings, cache_dir: Path, gate: PolitenessGate, name: str
) -> FetcherDeps:
    return FetcherDeps(
        settings=settings, cache_dir=cache_dir, gate=gate,
        breaker=CircuitBreaker(key=f"fetcher:{name}"),
    )


def build_fetchers(
    settings: Settings,
    conn: Connection,
    cache_dir: str | Path,
    *,
    gate: PolitenessGate | None = None,
) -> dict[str, Fetcher]:
    """Every fetcher, keyless ones included but disabled (06 §3.2)."""
    root = Path(cache_dir)
    shared = gate or PolitenessGate(
        rate_per_s=settings.fetch.per_domain_rate_limit_per_s,
        contact_email=settings.secrets.contact_email or "",
    )
    secrets = settings.secrets
    fetchers: dict[str, Fetcher] = {
        "web": WebFetcher(_deps(settings, root, shared, "web")),
        "wikipedia": WikipediaFetcher(_deps(settings, root, shared, "wikipedia")),
        "supplements": SupplementsFetcher(
            _deps(settings, root, shared, "supplements"), conn
        ),
        "courtlistener": CourtlistenerFetcher(
            _deps(settings, root, shared, "courtlistener"),
            secrets.courtlistener_token,
        ),
        "openalex": OpenAlexFetcher(_deps(settings, root, shared, "openalex")),
        "crossref": CrossrefFetcher(_deps(settings, root, shared, "crossref")),
        "google_factcheck": GoogleFactcheckFetcher(
            _deps(settings, root, shared, "google_factcheck"),
            secrets.google_factcheck_key,
        ),
        "tmdb": TmdbFetcher(
            _deps(settings, root, shared, "tmdb"), secrets.tmdb_api_key
        ),
        "openlibrary": OpenlibraryFetcher(
            _deps(settings, root, shared, "openlibrary")
        ),
        "musicbrainz": MusicbrainzFetcher(
            _deps(settings, root, shared, "musicbrainz")
        ),
    }
    return fetchers


def fetcher_status(fetchers: dict[str, Fetcher]) -> list[FetcherStatus]:
    """Enabled/disabled + reason per fetcher (CLI/doctor/report use)."""
    out: list[FetcherStatus] = []
    for name in sorted(fetchers):
        fetcher = fetchers[name]
        enabled = bool(getattr(fetcher, "enabled", True))
        if enabled:
            out.append(FetcherStatus(name=name, enabled=True, reason="ready"))
            continue
        reason = str(getattr(fetcher, "disabled_reason", "disabled"))
        out.append(FetcherStatus(name=name, enabled=False, reason=reason))
    return out
