"""Wikipedia fetcher: search, summaries, sections, reference leads (P07 T07.011).

`lookup` searches titles and returns the top summaries; `fetch_url` renders
the full article, or one section when the URL carries a `#Heading` fragment.
External reference URLs ride along as a trailing section (primary-source
leads for later stages).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import unquote, urldefrag, urlparse

import httpx
import trafilatura

from sots.models.evidence import FetchedDoc
from sots.research.fetchers.base import (
    FetcherDeps,
    clean_text,
    doc_hash,
    fetch_json,
    fetch_text,
)
from sots.research.fetchers.cache import read_cached, write_cached

logger = logging.getLogger(__name__)

API_URL = "https://en.wikipedia.org/w/api.php"
REST_URL = "https://en.wikipedia.org/api/rest_v1"
ARTICLE_URL = "https://en.wikipedia.org/wiki"
#: Summaries returned per lookup (candidates cap the rest).
TOP_K = 3
#: Reference leads kept per article.
MAX_REFS = 50

_HREF_RE = re.compile(r'href="(https?://[^"]+)"')
_HEADING_RE = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class WikipediaFetcher:
    """The MediaWiki backend (06 §3.2)."""

    name = "wikipedia"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top title matches as summary docs (06 §3.2)."""
        try:
            payload = await fetch_json(API_URL, deps=self._deps, params={
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": TOP_K, "format": "json",
            })
        except httpx.HTTPError as exc:
            logger.info("wikipedia lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in (payload.get("query", {}).get("search", []) or [])[:TOP_K]:
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            doc = await self.fetch_url(f"{ARTICLE_URL}/{title.replace(' ', '_')}")
            if doc is not None:
                docs.append(doc)
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """Full article, or one `#Heading` section (Plot/Themes/Reception)."""
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        clean, fragment = urldefrag(url)
        title = _title_from_url(clean)
        if title is None:
            return None
        try:
            html = await fetch_text(f"{REST_URL}/page/html/{title}", deps=self._deps)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("wikipedia fetch %s failed: %s", url, exc)
            return None
        if not html.strip():
            summary = await self._summary(title)
            if summary is None:
                return None
            write_cached(self._deps.cache_dir, summary)
            return summary
        section = _section_text(html, fragment) if fragment else None
        if fragment and section is None:
            return None  # unknown heading: no guesswork
        text = section if section is not None else _article_text(html)
        refs = reference_urls(html)
        if refs and section is None:
            text += "\n\nReferences:\n" + "\n".join(f"- {ref}" for ref in refs)
        text = clean_text(text, self._deps.settings.agents.injection_patterns)
        if not text.strip():
            return None
        doc = FetchedDoc(
            url=url, title=unquote(title).replace("_", " "), publisher="Wikipedia",
            published_date=None, text=text, content_hash=doc_hash(text),
            fetcher="wikipedia",
        )
        write_cached(self._deps.cache_dir, doc)
        return doc

    async def _summary(self, title: str) -> FetchedDoc | None:
        """The REST summary fallback when page HTML is unavailable."""
        try:
            payload = await fetch_json(
                f"{REST_URL}/page/summary/{title}", deps=self._deps
            )
        except httpx.HTTPError:
            return None
        if not isinstance(payload, dict) or not payload.get("extract"):
            return None
        text = clean_text(
            str(payload["extract"]), self._deps.settings.agents.injection_patterns
        )
        page = str((payload.get("content_urls") or {}).get("desktop", {}).get("page", ""))
        return FetchedDoc(
            url=page or f"{ARTICLE_URL}/{title}",
            title=str(payload.get("title", "")), publisher="Wikipedia",
            published_date=None, text=text, content_hash=doc_hash(text),
            fetcher="wikipedia",
        )


def _title_from_url(url: str) -> str | None:
    """The `/wiki/Title` path segment, or None for non-article URLs."""
    parts = urlparse(url)
    if parts.netloc.lower() != "en.wikipedia.org":
        return None
    if not parts.path.startswith("/wiki/"):
        return None
    title = parts.path[len("/wiki/"):]
    return title or None


def _inner_text(fragment: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub("", fragment)).strip()


def _section_text(html: str, fragment: str) -> str | None:
    """The section under `#Heading` (None when the heading is absent)."""
    want = unquote(fragment).replace("_", " ").lower()
    headings = [
        (match.start(), int(match.group(1)), _inner_text(match.group(2)).lower())
        for match in _HEADING_RE.finditer(html)
    ]
    for index, (start, level, text) in enumerate(headings):
        if text != want:
            continue
        end = len(html)
        for later_start, later_level, _ in headings[index + 1:]:
            if later_level <= level:
                end = later_start
                break
        body = html[start:end]
        text_out = trafilatura.extract(body) or _inner_text(body)
        return _WS_RE.sub(" ", text_out).strip() or None
    return None


def _article_text(html: str) -> str:
    return _WS_RE.sub(" ", trafilatura.extract(html) or _inner_text(html)).strip()


def reference_urls(html: str) -> list[str]:
    """External hrefs: reference leads for primary sources (06 §3.2)."""
    seen: list[str] = []
    for href in _HREF_RE.findall(html):
        host = urlparse(href).netloc.lower()
        if "wikipedia.org" in host or "wikimedia.org" in host:
            continue
        if href not in seen:
            seen.append(href)
        if len(seen) >= MAX_REFS:
            break
    return seen
