"""Generic web fetcher: HTML via trafilatura, PDFs via pypdf (P07 T07.010).

Robots.txt is respected, bodies cap at 5 MB (oversized fetches fail closed
to None), and non-HTML/non-PDF content is skipped. Full text lands in the
fetch cache; `lookup` is meaningless for the open web and raises.
"""

from __future__ import annotations

import io
import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
import trafilatura
from pypdf import PdfReader

from sots.agents.failsafes.f02_retry import with_retry
from sots.models.evidence import FetchedDoc
from sots.research.fetchers.base import FetcherDeps, clean_text, doc_hash
from sots.research.fetchers.cache import read_cached, write_cached

logger = logging.getLogger(__name__)

#: Response-body cap (F15); bigger pages fail closed.
MAX_BYTES = 5 * 1024 * 1024

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class _TextOnly(HTMLParser):
    """Last-resort text extraction when trafilatura finds nothing."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in ("script", "style", "nav", "footer"):
            self._skip += 1
        if tag in ("p", "br", "h1", "h2", "h3", "h4", "li", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        return _WS_RE.sub(" ", "".join(self._parts)).strip()


def _strip_fallback(html: str) -> str:
    parser = _TextOnly()
    parser.feed(html)
    return parser.text()


def _title_of(html: str) -> str:
    match = _TITLE_RE.search(html)
    if match is None:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub("", match.group(1))).strip()


class WebFetcher:
    """The open-web backend (06 §3.2)."""

    name = "web"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """The open web has no lookup API; search first, then fetch URLs."""
        raise NotImplementedError("web has no lookup; use fetch_url")

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """Fetch + extract + cache one URL (None when unusable)."""
        settings = self._deps.settings
        cached = read_cached(
            self._deps.cache_dir, url, ttl_days=settings.cache.fetch_ttl_days
        )
        if cached is not None:
            return cached
        gate = self._deps.gate
        timeout = httpx.Timeout(settings.fetch.timeout_s)
        headers = {"User-Agent": gate.user_agent}
        try:
            await gate.acquire(url)
            async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
                if not await gate.robots_allowed(url, lambda u: _fetch_robots(client, u)):
                    logger.info("web fetch blocked by robots.txt: %s", url)
                    return None
                await gate.acquire(url)
                body, content_type, final_url = await self._deps.breaker.call(
                    lambda: with_retry(lambda: _download(client, url))
                )
        except httpx.HTTPStatusError as exc:
            logger.info("web fetch %s -> HTTP %s", url, exc.response.status_code)
            return None
        except httpx.HTTPError as exc:
            logger.info("web fetch %s failed: %s", url, exc)
            return None
        if body is None:
            logger.info("web fetch %s exceeds the %d-byte cap", url, MAX_BYTES)
            return None
        if "pdf" in content_type or url.lower().endswith(".pdf"):
            doc = _pdf_doc(
                url, final_url, body,
                self._deps.settings.agents.injection_patterns,
            )
        elif "html" in content_type or "text" in content_type:
            doc = _html_doc(
                url, final_url, body,
                self._deps.settings.agents.injection_patterns,
            )
        else:
            logger.info("web fetch %s skipped: %r", url, content_type)
            return None
        if doc is None or not doc.text.strip():
            return None
        write_cached(self._deps.cache_dir, doc)
        return doc


async def _fetch_robots(client: httpx.AsyncClient, robots_url: str) -> str | None:
    """robots.txt text, or None on any failure (fail-open, logged)."""
    try:
        response = await client.get(robots_url, follow_redirects=True)
        if response.status_code != 200:
            return None
        return response.text
    except httpx.HTTPError as exc:
        logger.info("robots fetch failed for %s: %s", robots_url, exc)
        return None


async def _download(
    client: httpx.AsyncClient, url: str
) -> tuple[bytes | None, str, str]:
    """Streamed body (None when oversized) + content type + final URL."""
    async with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        raw_type = response.headers.get("content-type", "")
        content_type = raw_type.split(";")[0].strip().lower()
        final_url = str(response.url)
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_BYTES:
                return None, content_type, final_url
        return b"".join(chunks), content_type, final_url


def _html_doc(
    url: str, final_url: str, body: bytes, patterns: list[str]
) -> FetchedDoc | None:
    html = body.decode("utf-8", errors="replace")
    text = trafilatura.extract(html) or _strip_fallback(html)
    text = clean_text(text, patterns)
    if not text.strip():
        return None
    domain = urlparse(final_url).netloc.lower()
    return FetchedDoc(
        url=url, title=_title_of(html), publisher=domain or None,
        published_date=None, text=text, content_hash=doc_hash(text), fetcher="web",
    )


def _pdf_doc(
    url: str, final_url: str, body: bytes, patterns: list[str]
) -> FetchedDoc | None:
    try:
        reader = PdfReader(io.BytesIO(body))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        title = str(reader.metadata.title or "") if reader.metadata else ""
    except Exception as exc:  # corrupt PDFs are unusable, not fatal
        logger.info("web fetch %s: unreadable PDF (%s)", url, exc)
        return None
    text = clean_text(text, patterns)
    if not text.strip():
        return None
    domain = urlparse(final_url).netloc.lower()
    return FetchedDoc(
        url=url, title=title, publisher=domain or None, published_date=None,
        text=text, content_hash=doc_hash(text), fetcher="web",
    )
