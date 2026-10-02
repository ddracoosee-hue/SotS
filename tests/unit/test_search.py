"""P07 search provider tests (T07.001-T07.004, 04 §7)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from sots.config import load_settings
from sots.errors import ProviderNotConfiguredError
from sots.models.evidence import SearchHit
from sots.research.search.base import normalize_url, run_chain
from sots.research.search.muse_search import MuseSearchProvider
from sots.research.search.searxng import SearxngProvider
from sots.research.search.tavily import TavilyProvider

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def _hit(url: str, rank: int) -> SearchHit:
    return SearchHit(url=url, title=f"T{url}", snippet="S", rank=rank)


class _Fake:
    def __init__(self, name: str, hits: list[SearchHit] | None = None) -> None:
        self.name = name
        self._hits = hits

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        if self._hits is None:
            raise RuntimeError("boom")
        return self._hits[:max_results]


async def test_chain_merges_dedupes_reranks() -> None:
    """T07.001: merge in order, URL dedupe keeps best rank, re-rank 1..N."""
    first = _Fake("p1", [_hit("https://a.test/x", 1), _hit("https://b.test/y", 2)])
    second = _Fake("p2", [_hit("HTTPS://B.TEST/y#frag", 1), _hit("https://c.test/z", 2)])
    down = _Fake("p3")
    out = await run_chain([first, second, down], "q", 10)
    assert [(h.url, h.rank) for h in out.hits] == [
        ("https://a.test/x", 1),
        ("HTTPS://B.TEST/y#frag", 2),  # best rank wins; original URL kept
        ("https://c.test/z", 3),
    ]
    assert list(out.errors) == ["p3"]
    assert "boom" in out.errors["p3"]


def test_normalize_url() -> None:
    assert normalize_url("HTTPS://A.TEST/x/#f") == "https://a.test/x"
    assert normalize_url("http://a.test") == "http://a.test/"
    assert normalize_url("https://a.test/x?b=2&a=1") == "https://a.test/x?b=2&a=1"


@respx.mock
async def test_searxng_client() -> None:
    """T07.002: the JSON API shape maps to hits; empties skipped."""
    route = respx.get("http://sx.test/search", params={"q": "climate", "format": "json"}).mock(
        return_value=httpx.Response(200, json={"results": [
            {"url": "https://a.test/1", "title": "One", "content": "First"},
            {"url": "", "title": "No URL", "content": "skip me"},
            {"url": "https://b.test/2", "title": "Two", "content": "Second"},
        ]})
    )
    hits = await SearxngProvider("http://sx.test").search("climate", 10)
    assert route.called
    assert [(h.url, h.title, h.snippet, h.rank) for h in hits] == [
        ("https://a.test/1", "One", "First", 1),
        ("https://b.test/2", "Two", "Second", 3),
    ]
    capped = await SearxngProvider("http://sx.test").search("climate", 1)
    assert len(capped) == 1


@respx.mock
async def test_tavily_client_and_key() -> None:
    """T07.003: POST shape maps to hits; no key disables the provider."""
    route = respx.post("https://api.tavily.com/search").mock(
        return_value=httpx.Response(200, json={"results": [
            {"url": "https://a.test/1", "title": "One", "content": "First"},
        ]})
    )
    provider = TavilyProvider("KEY")
    assert provider.enabled is True
    hits = await provider.search("climate", 5)
    assert route.called
    assert [(h.url, h.rank) for h in hits] == [("https://a.test/1", 1)]
    body = json.loads(route.calls[0].request.content)
    assert body["api_key"] == "KEY" and body["query"] == "climate"

    off = TavilyProvider(None)
    assert off.enabled is False
    with pytest.raises(ProviderNotConfiguredError):
        await off.search("climate", 5)


async def test_muse_search_disabled_by_default() -> None:
    """T07.004: only an explicit true activates the stub."""
    assert MuseSearchProvider(None).enabled is False
    assert MuseSearchProvider(False).enabled is False
    assert MuseSearchProvider(True).enabled is True
    settings = load_settings(CONFIG_DIR, env_file=None)
    default = MuseSearchProvider(settings.providers.muse.supports_web_search)
    assert default.enabled is False
    with pytest.raises(ProviderNotConfiguredError):
        await default.search("q", 5)
    with pytest.raises(NotImplementedError, match="OI-03"):
        await MuseSearchProvider(True).search("q", 5)
