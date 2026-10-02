"""Crossref fetcher: DOI metadata + update/retraction notices (P07 T07.014).

Works search and DOI resolution; `update-to` relations and retraction
signals surface inline so verdict rules can see them. No key needed.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, urlparse

import httpx

from sots.models.evidence import FetchedDoc
from sots.research.fetchers.base import FetcherDeps, clean_text, doc_hash, fetch_json
from sots.research.fetchers.cache import read_cached, write_cached

logger = logging.getLogger(__name__)

API_URL = "https://api.crossref.org"
#: Works returned per lookup (candidates cap the rest).
TOP_K = 3

_DOI_RE = re.compile(r"^10\.\d{4,}/.+", re.IGNORECASE)


class CrossrefFetcher:
    """The Crossref backend (06 §3.2)."""

    name = "crossref"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    def _params(self, extra: dict[str, object]) -> dict[str, object]:
        email = self._deps.settings.secrets.contact_email
        params = dict(extra)
        if email:
            params["mailto"] = email  # the polite pool
        return params

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top works as metadata docs, updates inline (06 §3.2)."""
        try:
            payload = await fetch_json(
                f"{API_URL}/works", deps=self._deps,
                params=self._params({"query": query, "rows": TOP_K}),
            )
        except httpx.HTTPError as exc:
            logger.info("crossref lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in (payload.get("message", {}).get("items", []) or [])[:TOP_K]:
            doc = self._work_doc(item)
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One work by DOI URL (or a bare DOI)."""
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        doi = _doi_from_url(url)
        if doi is None:
            return None
        try:
            payload = await fetch_json(
                f"{API_URL}/works/{quote(doi, safe='')}", deps=self._deps,
                params=self._params({}),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("crossref fetch %s failed: %s", url, exc)
            return None
        message = payload.get("message", {})
        if not isinstance(message, dict) or not message.get("DOI"):
            return None
        doc = self._work_doc(message, url=url)
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc

    def _work_doc(self, item: dict[str, object], *, url: str | None = None) -> FetchedDoc | None:
        titles = item.get("title")
        title = str(next(iter(titles), "")) if isinstance(titles, list) else ""
        doi = str(item.get("DOI", "") or "")
        if not title or not doi:
            return None
        raw_authors = item.get("author")
        authors_list = raw_authors if isinstance(raw_authors, list) else []
        authors = ", ".join(
            " ".join(p for p in (a.get("given", ""), a.get("family", "")) if p).strip()
            for a in authors_list if isinstance(a, dict)
        )
        published = item.get("published")
        parts = published.get("date-parts", []) if isinstance(published, dict) else []
        year = next(iter(parts), []) if isinstance(parts, list) else []
        relation = item.get("relation")
        links = relation.get("update-to", []) if isinstance(relation, dict) else []
        updates = [
            str(link.get("id", "")) for link in links
            if isinstance(link, dict) and link.get("id")
        ]
        subtype = str(item.get("subtype", "") or "")
        retracted = "retraction" in subtype.lower() or "retraction" in str(title).lower()
        lines = [str(title)]
        if authors:
            lines.append(f"Authors: {authors}")
        if year:
            lines.append(f"Year: {year[0]}")
        lines.append(f"DOI: {doi}")
        lines.append(f"Updates: {', '.join(updates) if updates else 'none'}")
        lines.append(f"Retraction noticed: {'yes' if retracted else 'no'}")
        text = clean_text(
            "\n".join(lines), self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url or f"https://doi.org/{doi}", title=str(title), publisher=None,
            published_date=None, text=text, content_hash=doc_hash(text),
            fetcher="crossref",
        )


def _doi_from_url(url: str) -> str | None:
    """A DOI from a doi.org URL or a bare `10.x/...` string."""
    text = url.strip()
    if _DOI_RE.match(text):
        return text
    parts = urlparse(text)
    if parts.netloc.lower() in ("doi.org", "dx.doi.org"):
        doi = parts.path.lstrip("/")
        return doi if _DOI_RE.match(doi) else None
    return None
