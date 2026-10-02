"""Tool gating and execution (W0 split of agents/base.py)."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from sots.agents.context import AgentContext
from sots.agents.failsafes.f01_timeout import with_timeout
from sots.agents.failsafes.f02_retry import with_retry
from sots.agents.failsafes.f03_circuit import CircuitBreaker
from sots.agents.tools.base import ToolContext, get_tool, registered_tools
from sots.config import Settings
from sots.errors import ConfigError, ToolNotAllowedError
from sots.models.agents import AgentAction, Observation
from sots.storage.db import Connection


class BreakerPool:
    """Per-tool F03 breakers, created lazily per agent instance."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def for_tool(self, tool_name: str) -> CircuitBreaker:
        """Per-tool F03 breaker, created lazily per invocation."""
        breaker = self._breakers.get(tool_name)
        if breaker is None:
            breaker = CircuitBreaker(f"tool:{tool_name}")
            self._breakers[tool_name] = breaker
        return breaker


def validate_tool_action(ctx: AgentContext, action: AgentAction) -> str:
    """Tool allow-list gate (T03.012); returns the tool name or raises."""
    if action.type != "tool" or not action.tool:
        raise ToolNotAllowedError("step action is not a usable tool call")
    if action.tool not in ctx.card.tools:
        raise ToolNotAllowedError(
            f"tool {action.tool!r} is not in card {ctx.card.name!r} allow-list"
        )
    available = registered_tools()
    if action.tool not in available:
        raise ConfigError(f"tool {action.tool!r} is allowed but not registered")
    return action.tool


async def execute_tool(
    ctx: AgentContext,
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    settings: Settings,
    conn: Connection,
    data_dir: str,
    breaker: CircuitBreaker,
) -> Observation:
    """Run one tool (F02 > F03 > F01); failures become ok=False observations."""
    tool = get_tool(tool_name)
    try:
        validated = tool.args_model.model_validate(args or {})
    except ValidationError as exc:
        raise ToolNotAllowedError(f"tool {tool_name!r} args invalid: {exc}") from exc
    tool_ctx = ToolContext(
        run_id=ctx.run_id,
        document_id=None,
        settings=settings,
        conn=conn,
        data_dir=data_dir,
    )
    timeout_s = float(settings.agents.tool_timeout_s)

    async def _attempt() -> Observation:
        return await breaker.call(
            lambda: with_timeout(
                tool.run(validated, tool_ctx), timeout_s, f"tool {tool_name}"
            )
        )

    try:
        return await with_retry(_attempt)
    except Exception as exc:
        return Observation(
            tool=tool_name, ok=False,
            content=f"error: {type(exc).__name__}: {exc}", truncated=False,
        )
