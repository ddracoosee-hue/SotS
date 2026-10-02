"""SearchProvider protocol, registry, and merging chain (P07 T07.001, 04 §7).

The chain tries the enabled providers in settings order, merges every
success, dedupes by normalized URL keeping the best rank, and re-ranks the
merged list 1..N. Per-provider failures are recorded, never fatal.
"""

from __future__ import annotations

from typing import Protocol
from urllib.parse import urldefrag, urlparse

from pydantic import BaseModel, ConfigDict

from sots.errors import ConfigError
from sots.models.evidence import SearchHit


class SearchProvider(Protocol):
    """Search backend (04 §7)."""

    name: str

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        """Ranked hits for `query` (at most `max_results`)."""
        ...


_PROVIDERS: dict[str, SearchProvider] = {}


def register_search_provider(provider: SearchProvider) -> SearchProvider:
    """Register a search backend (implementations + test fakes)."""
    _PROVIDERS[provider.name] = provider
    return provider


def get_search_provider(name: str) -> SearchProvider:
    """Fetch a backend; unknown names raise ConfigError."""
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise ConfigError(f"search provider {name!r} is not registered") from exc


def registered_search_providers() -> dict[str, SearchProvider]:
    """Snapshot of the backend registry."""
    return dict(_PROVIDERS)


def clear_search_providers() -> None:
    """Empty the backend registry (tests only)."""
    _PROVIDERS.clear()


def normalize_url(url: str) -> str:
    """URL identity for dedupe: lowercased host, no fragment/trailing slash."""
    clean, _ = urldefrag(url.strip())
    parts = urlparse(clean)
    host = parts.netloc.lower()
    path = parts.path.rstrip("/") or "/"
    rebuilt = f"{parts.scheme.lower()}://{host}{path}"
    if parts.query:
        rebuilt += f"?{parts.query}"
    return rebuilt


class SearchChainOut(BaseModel):
    """Merged hits plus per-provider errors (04 §7)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hits: list[SearchHit]
    errors: dict[str, str]


async def run_chain(
    providers: list[SearchProvider], query: str, max_results: int
) -> SearchChainOut:
    """Query every provider in order; merge, dedupe, re-rank (04 §7)."""
    scored: list[tuple[int, int, SearchHit]] = []
    errors: dict[str, str] = {}
    for index, provider in enumerate(providers):
        try:
            hits = await provider.search(query, max_results)
        except Exception as exc:  # one backend must not sink the chain
            errors[provider.name] = f"{type(exc).__name__}: {exc}"
            continue
        for hit in hits:
            scored.append((hit.rank, index, hit))
    scored.sort(key=lambda item: (item[0], item[1]))
    merged: list[SearchHit] = []
    seen: set[str] = set()
    for _, _, hit in scored:
        key = normalize_url(hit.url)
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
    ranked = [
        hit.model_copy(update={"rank": rank})
        for rank, hit in enumerate(merged[:max_results], start=1)
    ]
    return SearchChainOut(hits=ranked, errors=errors)
