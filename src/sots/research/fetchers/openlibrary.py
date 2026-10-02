"""Open Library fetcher: books, authors, years (P07 T07.017).

Title search resolves works; the work record supplies the description,
authors, and first publish year. No key needed.
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

API_URL = "https://openlibrary.org"
#: Works returned per lookup (candidates cap the rest).
TOP_K = 3

_WORK_RE = re.compile(r"^(/works/OL\d+W)")


class OpenlibraryFetcher:
    """The Open Library backend (06 §3.2)."""

    name = "openlibrary"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top works as description docs (06 §3.2)."""
        try:
            payload = await fetch_json(
                f"{API_URL}/search.json", deps=self._deps,
                params={"q": query, "limit": TOP_K},
            )
        except httpx.HTTPError as exc:
            logger.info("openlibrary lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in payload.get("docs", []) or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "") or "")
            if not key.startswith("/works/"):
                continue
            doc = await self._work(key, search_hit=item)
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
            if len(docs) >= TOP_K:
                break
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One work by its openlibrary.org URL."""
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        parts = urlparse(url)
        match = _WORK_RE.match(parts.path)
        if parts.netloc.lower() != "openlibrary.org" or match is None:
            return None
        try:
            doc = await self._work(match.group(1), url=url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("openlibrary fetch %s failed: %s", url, exc)
            return None
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc

    async def _work(
        self, key: str, *, search_hit: dict[str, object] | None = None,
        url: str | None = None,
    ) -> FetchedDoc | None:
        payload = await fetch_json(f"{API_URL}{key}.json", deps=self._deps)
        title = str(payload.get("title", "") or "").strip()
        if not title:
            return None
        description = payload.get("description", "")
        if isinstance(description, dict):
            description = description.get("value", "")
        authors = ", ".join(
            str(a.get("name", "?")) for a in self._hit_authors(search_hit)
        )
        year = self._hit_year(search_hit)
        lines = [title]
        if authors:
            lines.append(f"Authors: {authors}")
        if year:
            lines.append(f"First published: {year}")
        if description:
            lines.append(f"\nDescription: {description}")
        text = clean_text(
            "\n".join(lines), self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url or f"{API_URL}{key}", title=title, publisher="Open Library",
            published_date=None, text=text, content_hash=doc_hash(text),
            fetcher="openlibrary",
        )

    @staticmethod
    def _hit_authors(hit: dict[str, object] | None) -> list[dict[str, object]]:
        if not hit:
            return []
        names = hit.get("author_name")
        if not isinstance(names, list):
            return []
        return [{"name": str(name)} for name in names]

    @staticmethod
    def _hit_year(hit: dict[str, object] | None) -> int | None:
        if not hit:
            return None
        year = hit.get("first_publish_year")
        return year if isinstance(year, int) else None
