"""OpenAlex fetcher: works, abstracts, retractions (P07 T07.013).

Works search returns docs carrying the reconstructed abstract inline; the
contact email rides in the User-Agent per OpenAlex policy. Disabled never:
no key is needed.
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

API_URL = "https://api.openalex.org"
#: Works returned per lookup (candidates cap the rest).
TOP_K = 3

_WORK_RE = re.compile(r"^/works/(W\d+)/?$", re.IGNORECASE)


class OpenAlexFetcher:
    """The OpenAlex backend (06 §3.2)."""

    name = "openalex"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    def _headers(self) -> dict[str, str]:
        email = self._deps.settings.secrets.contact_email
        if email:
            return {"User-Agent": f"SotS research fetcher (mailto:{email})"}
        return {}

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top works as abstract docs (06 §3.2)."""
        try:
            payload = await fetch_json(
                f"{API_URL}/works", deps=self._deps,
                params={"search": query, "per-page": TOP_K},
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            logger.info("openalex lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in (payload.get("results", []) or [])[:TOP_K]:
            doc = _work_doc(item, self._deps.settings.agents.injection_patterns)
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One work by its OpenAlex (or DOI) URL."""
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        work_id = _work_id_from_url(url)
        if work_id is None:
            return None
        try:
            payload = await fetch_json(
                f"{API_URL}/works/{work_id}", deps=self._deps,
                headers=self._headers(),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("openalex fetch %s failed: %s", url, exc)
            return None
        if not isinstance(payload, dict) or not payload.get("id"):
            return None
        doc = _work_doc(payload, self._deps.settings.agents.injection_patterns, url=url)
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc


def _work_id_from_url(url: str) -> str | None:
    """An OpenAlex work id, DOI path, or None for foreign URLs."""
    parts = urlparse(url)
    host = parts.netloc.lower()
    if host in ("openalex.org", "api.openalex.org"):
        match = _WORK_RE.match(parts.path)
        return match.group(1).upper() if match else None
    if host == "doi.org":
        doi = parts.path.lstrip("/")
        return doi or None
    return None


def reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    """Rebuild an abstract from its inverted index (06 §3.2)."""
    if not inverted:
        return ""
    positions: dict[int, str] = {}
    for word, indices in inverted.items():
        for index in indices:
            positions[index] = word
    return " ".join(positions[i] for i in sorted(positions))


def _work_doc(
    item: dict[str, object], patterns: list[str], *, url: str | None = None
) -> FetchedDoc | None:
    title = str(item.get("title") or item.get("display_name") or "").strip()
    if not title:
        return None
    work_id = str(item.get("id", ""))
    raw_authors = item.get("authorships")
    authorships = raw_authors if isinstance(raw_authors, list) else []
    authors = ", ".join(
        str((a.get("author") or {}).get("display_name", "?"))
        for a in authorships if isinstance(a, dict)
    )
    year = item.get("publication_year")
    venue = str((item.get("primary_location") or {}).get("source", {}).get(
        "display_name", "") or "")
    doi = str(item.get("doi", "") or "")
    cited = item.get("cited_by_count", 0)
    retracted = bool(item.get("is_retracted"))
    raw_index = item.get("abstract_inverted_index")
    inverted = raw_index if isinstance(raw_index, dict) else None
    abstract = reconstruct_abstract(inverted)
    lines = [title]
    if authors:
        lines.append(f"Authors: {authors}")
    if year:
        lines.append(f"Year: {year}")
    if venue:
        lines.append(f"Venue: {venue}")
    if doi:
        lines.append(f"DOI: {doi}")
    lines.append(f"Cited by: {cited}")
    lines.append(f"Retracted: {'yes' if retracted else 'no'}")
    if abstract:
        lines.append(f"\nAbstract: {abstract}")
    text = clean_text("\n".join(lines), patterns)
    doc_url = url or work_id or doi
    return FetchedDoc(
        url=doc_url, title=title, publisher=venue or None, published_date=None,
        text=text, content_hash=doc_hash(text), fetcher="openalex",
    )
