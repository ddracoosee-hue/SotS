"""Structured-lookup placeholders delegating to P07 fetchers (P03 T03.029, 16 §3).

courtlistener / openalex / crossref / google_factcheck / tmdb / openlibrary /
musicbrainz / wikipedia: registered now so cards can name them; each `run`
reports "not implemented" until its P07 fetcher lands.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import Tool, ToolContext, register_tool
from sots.models.agents import Observation

LOOKUP_TOOLS: tuple[str, ...] = (
    "courtlistener",
    "openalex",
    "crossref",
    "google_factcheck",
    "tmdb",
    "openlibrary",
    "musicbrainz",
    "wikipedia",
)


class LookupArgs(BaseModel):
    """Lookup query (per-fetcher fields arrive with P07)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str


def _make_lookup_tool(tool_name: str) -> Tool:
    class _LookupTool:
        name = tool_name
        internet = True
        args_model = LookupArgs

        async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
            assert isinstance(args, LookupArgs)
            _ = (ctx, args)
            return Observation(
                tool=tool_name, ok=False,
                content=json.dumps({"error": f"{tool_name} fetcher lands in P07"}),
                truncated=False,
            )

    _LookupTool.__name__ = f"{tool_name.title().replace('_', '')}LookupTool"
    return _LookupTool()  # type: ignore[return-value]


def lookup_tools() -> dict[str, Any]:
    """The eight placeholder tools (registry + tests)."""
    return {name: _make_lookup_tool(name) for name in LOOKUP_TOOLS}


for _tool in lookup_tools().values():
    register_tool(_tool)
