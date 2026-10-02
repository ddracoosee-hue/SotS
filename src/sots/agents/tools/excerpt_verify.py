"""`excerpt_verify` stub over the P07 citation check (P03 T03.028, 16 §3).

`verify_excerpt` keeps the exact `verify/citation_check.py` signature from
T07.031 (`(doc_text, excerpt) -> (ok, score)`); the real implementation lands
in P07. Until then the tool reports "not implemented" instead of guessing.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation


def verify_excerpt(doc_text: str, excerpt: str) -> tuple[bool, float]:
    """Stub for T07.031: normalize + exact/partial matching (P07 implements)."""
    _ = (doc_text, excerpt)
    raise NotImplementedError("verify/citation_check.py lands in P07 (T07.031)")


class ExcerptVerifyArgs(BaseModel):
    """Source text plus the excerpt claimed to come from it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_text: str
    excerpt: str


class ExcerptVerifyTool:
    """`excerpt_verify`: deterministic citation check (stubbed until P07)."""

    name = "excerpt_verify"
    internet = False
    args_model = ExcerptVerifyArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, ExcerptVerifyArgs)
        _ = ctx
        try:
            ok, score = verify_excerpt(args.doc_text, args.excerpt)
        except NotImplementedError as exc:
            return Observation(tool=self.name, ok=False, content=f"error: {exc}", truncated=False)
        return Observation(
            tool=self.name, ok=True,
            content=json.dumps({"ok": ok, "score": score}), truncated=False,
        )


register_tool(ExcerptVerifyTool())
