"""`web_search` tool over the SearchProvider chain (P03 T03.021, 16 §3, 04 §7).

Tries `settings.search.providers` in order; the first success wins. Unknown or
failing providers are skipped with a note (P07 registers the real searxng /
tavily implementations). Results are capped at 10; queries are logged.
Snippets only decide which URLs to fetch — never evidence (R-TRUTH-02).
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.errors import ConfigError
from sots.models.agents import Observation
from sots.research.search.base import (
    SearchProvider,  # noqa: F401  (re-exported for tool code + tests)
    clear_search_providers,  # noqa: F401
    get_search_provider,
    register_search_provider,  # noqa: F401
    registered_search_providers,  # noqa: F401
)

logger = logging.getLogger(__name__)

MAX_RESULTS = 10


class WebSearchArgs(BaseModel):
    """Query plus a result cap (clamped to 10)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    max_results: int = 10


class WebSearchTool:
    """`web_search`: the provider chain in settings order (16 §3)."""

    name = "web_search"
    internet = True
    args_model = WebSearchArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, WebSearchArgs)
        limit = min(max(1, args.max_results), MAX_RESULTS)
        logger.info("web_search query=%r max_results=%d", args.query, limit)
        skipped: list[str] = []
        for name in ctx.settings.search.providers:
            try:
                provider = get_search_provider(name)
            except ConfigError:
                skipped.append(f"{name}: not registered")
                continue
            try:
                hits = await provider.search(args.query, limit)
            except Exception as exc:  # one backend must not sink the chain
                skipped.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
            payload = {
                "query": args.query,
                "provider": name,
                "skipped": skipped,
                "hits": [hit.model_dump(mode="json") for hit in hits[:limit]],
            }
            return Observation(
                tool=self.name, ok=True, content=json.dumps(payload), truncated=False
            )
        detail = "; ".join(skipped) if skipped else "no search providers configured"
        return Observation(
            tool=self.name, ok=False, content=f"error: all providers failed ({detail})",
            truncated=False,
        )


register_tool(WebSearchTool())
