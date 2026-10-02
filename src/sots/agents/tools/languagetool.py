"""`languagetool` placeholder (P03 T03.030, 16 §3; implemented in P15).

Registered now so cards can name it; `run` reports "not implemented" until
the P15 local-server client lands. Local only: text never leaves the machine.
"""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation


class LanguageToolArgs(BaseModel):
    """Text to check (options arrive with P15)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str


class LanguageToolTool:
    """`languagetool`: spelling/grammar over the local server (stubbed)."""

    name = "languagetool"
    internet = False
    args_model = LanguageToolArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, LanguageToolArgs)
        _ = (ctx, args)
        return Observation(
            tool=self.name, ok=False,
            content=json.dumps({"error": "languagetool client lands in P15"}),
            truncated=False,
        )


async def ping(url: str, timeout_s: float = 3.0) -> None:
    """Probe the local LanguageTool server; raises on any failure.

    The doctor (F17) calls this so HTTP stays inside `agents/tools/`.
    """
    target = url.rstrip("/")
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s)) as client:
        response = await client.get(f"{target}/v2/languages")
        response.raise_for_status()


register_tool(LanguageToolTool())
