"""MusicBrainz fetcher: recordings and releases (P07 T07.018).

Recording/release search with artist and date; metadata only, never audio.
**No lyrics**: no lyric endpoint exists here by design (copyright), and a
test pins that down. UA required, 1 rps via the shared gate. No key needed.
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

API_URL = "https://musicbrainz.org/ws/2"
#: Works returned per lookup (candidates cap the rest).
TOP_K = 3
#: The only API paths this fetcher may call (no lyric endpoints, ever).
ALLOWED_PATHS = ("/ws/2/recording", "/ws/2/release")

_MBID_RE = re.compile(
    r"^/(recording|release)/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


class MusicbrainzFetcher:
    """The MusicBrainz backend: metadata, never lyrics (06 §3.2)."""

    name = "musicbrainz"

    def __init__(self, deps: FetcherDeps) -> None:
        self._deps = deps

    async def lookup(self, query: str) -> list[FetchedDoc]:
        """Top recordings as metadata docs (06 §3.2)."""
        try:
            payload = await fetch_json(
                f"{API_URL}/recording/", deps=self._deps,
                params={"query": query, "fmt": "json", "limit": TOP_K},
            )
        except httpx.HTTPError as exc:
            logger.info("musicbrainz lookup %r failed: %s", query, exc)
            return []
        docs: list[FetchedDoc] = []
        for item in payload.get("recordings", []) or []:
            if not isinstance(item, dict):
                continue
            doc = self._recording_doc(item)
            if doc is not None:
                write_cached(self._deps.cache_dir, doc)
                docs.append(doc)
            if len(docs) >= TOP_K:
                break
        return docs

    async def fetch_url(self, url: str) -> FetchedDoc | None:
        """One recording/release by its musicbrainz.org URL."""
        cached = read_cached(
            self._deps.cache_dir, url,
            ttl_days=self._deps.settings.cache.fetch_ttl_days,
        )
        if cached is not None:
            return cached
        parts = urlparse(url)
        match = _MBID_RE.match(parts.path)
        if parts.netloc.lower() != "musicbrainz.org" or match is None:
            return None
        kind, mbid = match.group(1).lower(), match.group(2).lower()
        try:
            payload = await fetch_json(
                f"{API_URL}/{kind}/{mbid}", deps=self._deps,
                params={"fmt": "json", "inc": "artists+releases"},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        except httpx.HTTPError as exc:
            logger.info("musicbrainz fetch %s failed: %s", url, exc)
            return None
        doc = self._recording_doc(payload, url=url)
        if doc is not None:
            write_cached(self._deps.cache_dir, doc)
        return doc

    def _recording_doc(
        self, item: dict[str, object], *, url: str | None = None
    ) -> FetchedDoc | None:
        title = str(item.get("title", "") or "").strip()
        mbid = str(item.get("id", "") or "")
        if not title or not mbid:
            return None
        credit = item.get("artist-credit")
        artists_list = credit if isinstance(credit, list) else []
        artists = ", ".join(
            str(a.get("name", "?")) for a in artists_list
            if isinstance(a, dict) and a.get("name")
        )
        releases = item.get("releases", []) if isinstance(
            item.get("releases"), list) else []
        first = next((r for r in releases if isinstance(r, dict)), {})
        release = str(first.get("title", "") or "")
        date = str(first.get("date", "") or "")
        lines = [f"Recording: {title}"]
        if artists:
            lines.append(f"Artist: {artists}")
        if release:
            lines.append(f"Release: {release}" + (f" ({date})" if date else ""))
        lines.append(f"MBID: {mbid}")
        text = clean_text(
            "\n".join(lines), self._deps.settings.agents.injection_patterns
        )
        return FetchedDoc(
            url=url or f"https://musicbrainz.org/recording/{mbid}",
            title=title, publisher="MusicBrainz", published_date=None,
            text=text, content_hash=doc_hash(text), fetcher="musicbrainz",
        )
