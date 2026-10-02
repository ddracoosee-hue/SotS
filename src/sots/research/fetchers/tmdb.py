"""TMDB fetcher: films and TV details + credits (P07 T07.016).

Multi-search resolves titles; details and credits flesh out the doc
(title, year, overview, director, cast). Disabled without TMDB_API_KEY.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx

from sots.models.evidence import FetchedDoc
from sots.research.fetchers.base import FetcherDeps, clean_text, doc_hash, fetch_json
from sots.research.fetchers.cache import read_cached, write_cached

logger = logging.getLogger(__name__)

API_URL = "https://api.themoviedb.org/3"
#: Titles resolved per lookup (candidates cap the rest).
TOP_K = 3

_PATH_RE = re.compile(r"^/(movie|tv)/(\d+)")


class TmdbFetcher:
    """The TMDB backend (06 §3.2)."""

    name = "tmdb"

    def __init__(self, deps: FetcherDeps, api_key: str | None) -> None:
        self._deps = deps
        self.api_key = api_key

    @property
    def enabled(self) -> bool:
        """TMDB needs a (free) API key."""
        return bool(self.api_key)

    @property
    def disabled_reason(self) -> str:
        """Why this fetcher is unavailable (registry status use)."""
        return "missing TMDB_API_KEY"

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top film/TV matches as detail docs (06 §3.2)."""
        if not self.enabled:
            return []
        try:
            payload = await fetch_json(
                f"{API_URL}/search/multi", deps=self._deps,
                params={"api_key": self.api_key, "query": query},
            )
        except httpx.HTTPError as exc:
            logger.info("tmdb lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in payload.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("media_type", "") or "")
            item_id = item.get("id")
            if kind not in ("movie", "tv") or item_id is None:
                continue
            doc = await self._details(kind, int(item_id))
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
            if len(docs) >= TOP_K:
                break
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One title by its themoviedb.org URL."""
        if not self.enabled:
            return None
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        match = _PATH_RE.match(urlparse(url).path)
        if urlparse(url).netloc.lower() != "www.themoviedb.org" or match is None:
            return None
        try:
            doc = await self._details(match.group(1), int(match.group(2)), url=url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("tmdb fetch %s failed: %s", url, exc)
            return None
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc

    async def _details(
        self, kind: str, item_id: int, *, url: str | None = None
    ) -> FetchedDoc | None:
        details = await fetch_json(
            f"{API_URL}/{kind}/{item_id}", deps=self._deps,
            params={"api_key": self.api_key},
        )
        credits = await fetch_json(
            f"{API_URL}/{kind}/{item_id}/credits", deps=self._deps,
            params={"api_key": self.api_key},
        )
        title = str(details.get("title") or details.get("name") or "").strip()
        if not title:
            return None
        date = str(details.get("release_date") or details.get("first_air_date") or "")
        crew = credits.get("crew", []) if isinstance(credits, dict) else []
        directors = ", ".join(
            str(p.get("name", "?")) for p in crew
            if isinstance(p, dict) and p.get("job") == "Director"
        )
        cast_list = credits.get("cast", []) if isinstance(credits, dict) else []
        cast = ", ".join(
            str(p.get("name", "?")) for p in cast_list
            if isinstance(p, dict))[:500]
        lines = [f"{title} ({date[:4] if date else '?'}) [{kind}]"]
        if directors:
            lines.append(f"Director: {directors}")
        if cast:
            lines.append(f"Cast: {cast}")
        overview = str(details.get("overview", "") or "").strip()
        if overview:
            lines.append(f"\nOverview: {overview}")
        text = clean_text(
            "\n".join(lines), self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url or f"https://www.themoviedb.org/{kind}/{item_id}",
            title=title, publisher="TMDB", published_date=None,
            text=text, content_hash=doc_hash(text), fetcher="tmdb",
        )
