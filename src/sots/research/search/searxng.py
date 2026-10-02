"""SearXNG search provider (P07 T07.002, 04 §7).

Self-hosted JSON API: `GET {base}/search?format=json`. Registered as
`searxng`; snippets only decide which URLs to fetch (R-TRUTH-02).
"""

from __future__ import annotations

import httpx

from sots.models.evidence import SearchHit


class SearxngProvider:
    """SearXNG backend (04 §7)."""

    name = "searxng"

    def __init__(self, base_url: str, *, timeout_s: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        """Ranked hits via `/search?format=json`."""
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
        hits: list[SearchHit] = []
        for rank, item in enumerate(payload.get("results", []), start=1):
            if rank > max_results:
                break
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            hits.append(SearchHit(
                url=url, title=str(item.get("title", "")),
                snippet=str(item.get("content", "")), rank=rank,
            ))
        return hits
