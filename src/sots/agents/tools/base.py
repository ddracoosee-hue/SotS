"""Tool protocol, context, and registry (P03 T03.020, 16 §3).

Tools are the only way agents touch the outside world. Every tool declares a
name, an internet flag, a Pydantic args model, and an async `run`. Agents
never write to the DB directly; `db_read_*` tools are read-only and scoped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from sots.config import Settings
from sots.errors import ConfigError
from sots.models.agents import Observation
from sots.storage.db import Connection


@dataclass(frozen=True)
class ToolContext:
    """Wiring every tool call receives (run scope + services)."""

    run_id: str
    document_id: str | None
    settings: Settings
    conn: Connection | None = None
    data_dir: str = "data"
    profile_dir: str = "profile"


class Tool[T: BaseModel](Protocol):
    """What every tool implements (16 §3)."""

    name: str
    internet: bool
    args_model: type[T]

    async def run(self, args: T, ctx: ToolContext) -> Observation:
        """Execute with validated args; failures return ok=False observations."""
        ...


_TOOLS: dict[str, Tool[Any]] = {}


def register_tool(tool: Tool[Any]) -> Tool[Any]:
    """Register a tool instance under its name (duplicate names rejected)."""
    if tool.name in _TOOLS:
        raise ValueError(f"tool {tool.name!r} is already registered")
    _TOOLS[tool.name] = tool
    return tool


def get_tool(name: str) -> Tool[Any]:
    """Fetch a registered tool; unknown names raise ConfigError."""
    try:
        return _TOOLS[name]
    except KeyError as exc:
        raise ConfigError(f"tool {name!r} is not registered") from exc


def registered_tools() -> dict[str, Tool[Any]]:
    """Snapshot of the registry (cards validation, doctor, tests)."""
    return dict(_TOOLS)


def clear_registry() -> None:
    """Empty the registry (tests only)."""
    _TOOLS.clear()


def cache_path(ctx: ToolContext, *parts: str) -> Path:
    """Path under the fetch cache dir (`data/cache/...`)."""
    return Path(ctx.data_dir) / "cache" / Path(*parts)
