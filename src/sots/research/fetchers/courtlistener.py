"""CourtListener fetcher: cases, opinions, dockets (P07 T07.012).

Search API v4 by case name; opinion URLs resolve to full opinion text with
the case card (name, court, date filed, docket, citation); docket URLs
resolve to the procedural history. Disabled without COURTLISTENER_TOKEN.
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

API_URL = "https://www.courtlistener.com/api/rest/v4"
SITE_URL = "https://www.courtlistener.com"
#: Case cards returned per lookup (candidates cap the rest).
TOP_K = 3

_OPINION_RE = re.compile(r"^/opinion/(\d+)/")
_DOCKET_RE = re.compile(r"^/docket/(\d+)/")


class CourtlistenerFetcher:
    """The CourtListener backend (06 §3.2)."""

    name = "courtlistener"

    def __init__(self, deps: FetcherDeps, token: str | None) -> None:
        self._deps = deps
        self.token = token

    @property
    def enabled(self) -> bool:
        """CourtListener needs a (free) API token."""
        return bool(self.token)

    @property
    def disabled_reason(self) -> str:
        """Why this fetcher is unavailable (registry status use)."""
        return "missing COURTLISTENER_TOKEN"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.token}"}

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top case matches as case-card docs (06 §3.2)."""
        if not self.enabled:
            return []
        try:
            payload = await fetch_json(
                f"{API_URL}/search/", deps=self._deps,
                params={"q": query, "type": "o", "page_size": TOP_K},
                headers=self._headers(),
            )
        except httpx.HTTPError as exc:
            logger.info("courtlistener lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in (payload.get("results", []) or [])[:TOP_K]:
            doc = _case_card(item)
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """Opinion text or docket history for a CourtListener URL."""
        if not self.enabled:
            return None
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        path = urlparse(url).path
        opinion = _OPINION_RE.match(path)
        docket = _DOCKET_RE.match(path)
        try:
            if opinion is not None:
                doc = await self._opinion(url, opinion.group(1))
            elif docket is not None:
                doc = await self._docket(url, docket.group(1))
            else:
                return None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("courtlistener fetch %s failed: %s", url, exc)
            return None
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc

    async def _opinion(self, url: str, opinion_id: str) -> FetchedDoc | None:
        payload = await fetch_json(
            f"{API_URL}/opinions/{opinion_id}/", deps=self._deps,
            headers=self._headers(),
        )
        cluster = payload.get("cluster") or {}
        text = str(payload.get("plain_text") or payload.get("html") or "").strip()
        if not text:
            return None
        card = _card_lines({
            "case_name": cluster.get("case_name") or payload.get("case_name"),
            "court": cluster.get("court") or payload.get("court"),
            "date_filed": cluster.get("date_filed") or payload.get("date_filed"),
            "docket_number": cluster.get("docket_number"),
            "citation": cluster.get("citation"),
        })
        full = clean_text(
            card + "\n\n" + text, self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url, title=str(cluster.get("case_name") or f"Opinion {opinion_id}"),
            publisher="CourtListener", published_date=None, text=full,
            content_hash=doc_hash(full), fetcher="courtlistener",
        )

    async def _docket(self, url: str, docket_id: str) -> FetchedDoc | None:
        payload = await fetch_json(
            f"{API_URL}/dockets/{docket_id}/", deps=self._deps,
            headers=self._headers(),
        )
        entries = payload.get("entries") or []
        lines = [
            f"{entry.get('date_filed', '?')}: {entry.get('description', '?')}"
            for entry in entries
        ]
        card = _card_lines({
            "case_name": payload.get("case_name"),
            "court": payload.get("court"),
            "date_filed": payload.get("date_filed"),
            "docket_number": payload.get("docket_number"),
            "citation": None,
        })
        full = clean_text(
            card + "\n\nProcedural history:\n" + "\n".join(lines or ["(no entries)"]),
            self._deps.settings.agents.injection_patterns,
        )
        return FetchedDoc(
            url=url, title=str(payload.get("case_name") or f"Docket {docket_id}"),
            publisher="CourtListener", published_date=None, text=full,
            content_hash=doc_hash(full), fetcher="courtlistener",
        )


def _card_lines(fields: dict[str, object]) -> str:
    labels = (
        ("case_name", "Case"), ("court", "Court"), ("date_filed", "Date filed"),
        ("docket_number", "Docket"), ("citation", "Citation"),
    )
    return "\n".join(
        f"{label}: {fields[key]}" for key, label in labels if fields.get(key)
    )


def _case_card(item: dict[str, object]) -> FetchedDoc | None:
    name = item.get("case_name")
    opinion_url = item.get("absolute_url") or item.get("url")
    if not name or not opinion_url:
        return None
    url = opinion_url if str(opinion_url).startswith("http") else f"{SITE_URL}{opinion_url}"
    text = _card_lines({
        "case_name": name, "court": item.get("court"),
        "date_filed": item.get("date_filed"),
        "docket_number": item.get("docket_number"),
        "citation": item.get("citation"),
    })
    snippet = str(item.get("snippet") or item.get("text") or "").strip()
    if snippet:
        text += f"\n\n{snippet}"
    return FetchedDoc(
        url=url, title=str(name), publisher="CourtListener", published_date=None,
        text=text, content_hash=doc_hash(text), fetcher="courtlistener",
    )
