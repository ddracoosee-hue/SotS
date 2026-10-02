"""Tavily search provider (P07 T07.003, 04 §7).

Hosted API (`POST /search`); disabled without a key (the chain records the
skip and tries the next provider). Registered as `tavily`.
"""

from __future__ import annotations

import httpx

from sots.errors import ProviderNotConfiguredError
from sots.models.evidence import SearchHit

API_URL = "https://api.tavily.com/search"


class TavilyProvider:
    """Tavily backend (04 §7)."""

    name = "tavily"

    def __init__(self, api_key: str | None, *, timeout_s: float = 15.0) -> None:
        self.api_key = api_key
        self.timeout_s = timeout_s

    @property
    def enabled(self) -> bool:
        """Tavily needs a key; without one the provider is disabled."""
        return bool(self.api_key)

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        """Ranked hits via the hosted search API."""
        if not self.api_key:
            raise ProviderNotConfiguredError("tavily needs TAVILY_API_KEY")
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(API_URL, json={
                "api_key": self.api_key, "query": query,
                "max_results": max_results, "include_answer": False,
            })
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
