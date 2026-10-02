"""Muse web-search stub (P07 T07.004, 04 §7, 15 OI-03).

Activates only when `providers.muse.supports_web_search` is true; until the
Muse API offers search, calls fail closed with a clear error.
"""

from __future__ import annotations

from sots.errors import ProviderNotConfiguredError
from sots.models.evidence import SearchHit


class MuseSearchProvider:
    """Muse search backend (a stub until OI-03 resolves)."""

    name = "muse_search"

    def __init__(self, supports_web_search: bool | None) -> None:
        self.supports_web_search = supports_web_search

    @property
    def enabled(self) -> bool:
        """Only an explicit `true` activates this backend (OI-03)."""
        return self.supports_web_search is True

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        """Refuse: the Muse API does not offer search (OI-03)."""
        if not self.enabled:
            raise ProviderNotConfiguredError(
                "muse_search is disabled (supports_web_search is not true)"
            )
        raise NotImplementedError("Muse web search is not available yet (OI-03)")
