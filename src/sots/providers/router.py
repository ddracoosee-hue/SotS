"""Task routing with provider fallback (P02 T02.010, 04 §3).

`resolve()` maps a routing key to a concrete provider/model/params triple. When
the preferred provider is not configured, the router walks `fallback_order`
and records `fallback_used` on the route (persisted on the LLMCall row, 04 §3).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from sots.config import Settings
from sots.errors import ConfigError, ProviderNotConfiguredError
from sots.providers.base import LLMProvider
from sots.providers.local_ollama import OllamaProvider
from sots.providers.muse import MuseProvider


class RoutingTask(BaseModel):
    """One task entry in routing.yaml (model names live in settings)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    temperature: float
    max_output_tokens: int


class RoutingConfig(BaseModel):
    """Parsed routing.yaml: fallback order + per-task entries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fallback_order: list[str]
    tasks: dict[str, RoutingTask]


class ResolvedRoute(BaseModel):
    """Concrete call target plus whether a fallback was used (04 §3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    provider: str
    model: str
    temperature: float
    max_output_tokens: int
    fallback_used: bool = False
    preferred_provider: str = ""


def load_routing(path: str | Path) -> RoutingConfig:
    """Parse routing.yaml; missing/invalid files raise ConfigError."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ConfigError(f"routing file not found: {candidate}")
    try:
        raw = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse {candidate}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{candidate} must parse to a mapping")
    try:
        fallback = list((raw.get("defaults") or {}).get("fallback_order", []))
        tasks = {
            name: RoutingTask.model_validate(entry)
            for name, entry in (raw.get("tasks") or {}).items()
        }
        return RoutingConfig(fallback_order=fallback, tasks=tasks)
    except ValueError as exc:
        raise ConfigError(f"invalid routing in {candidate}: {exc}") from exc


def build_registry(settings: Settings) -> dict[str, LLMProvider]:
    """Real providers from settings (fake is test-only and never registered)."""
    local = OllamaProvider(
        base_url=settings.providers.local.base_url,
        model=settings.providers.local.model,
        num_ctx=settings.providers.local.num_ctx,
        context_window=settings.providers.local.context_window,
        timeout_s=settings.fetch.timeout_s,
    )
    muse = MuseProvider(settings.providers.muse, settings.secrets.muse_api_key)
    return {"local": local, "muse": muse}


def resolve(
    task: str,
    *,
    routing: RoutingConfig,
    registry: Mapping[str, LLMProvider],
) -> ResolvedRoute:
    """Resolve a task to provider/model/params, honoring fallback_order.

    The provider object is the single source of truth for readiness and the
    model name. Raises ConfigError for unknown tasks and
    ProviderNotConfiguredError when no provider in the chain can serve.
    """
    entry = routing.tasks.get(task)
    if entry is None:
        raise ConfigError(f"unknown routing task {task!r}")
    chain = [entry.provider] + [p for p in routing.fallback_order if p != entry.provider]
    for name in chain:
        provider = registry.get(name)
        if provider is None or not provider.configured or not provider.model:
            continue
        return ResolvedRoute(
            task=task,
            provider=name,
            model=provider.model,
            temperature=entry.temperature,
            max_output_tokens=entry.max_output_tokens,
            fallback_used=name != entry.provider,
            preferred_provider=entry.provider,
        )
    raise ProviderNotConfiguredError(
        f"no configured provider for task {task!r} "
        f"(preferred {entry.provider}, tried {', '.join(chain)})"
    )


def task_names(routing: RoutingConfig) -> list[str]:
    """Sorted routing task keys (used to check TASK_PIECES coverage)."""
    return sorted(routing.tasks)


def routing_entry_to_dict(entry: RoutingTask) -> dict[str, Any]:
    """RoutingTask back to plain data (report/debug use)."""
    return entry.model_dump()
