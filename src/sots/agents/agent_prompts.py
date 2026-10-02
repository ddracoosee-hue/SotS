"""Output-model and prompt resolution (W0 split of agents/base.py)."""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from sots.errors import ConfigError
from sots.models.agents import AgentCard
from sots.providers import prompts as prompt_loader
from sots.providers.context_pack import ContextPack

if TYPE_CHECKING:
    from sots.agents.context import AgentContext

_PROMPT_REF_RE = re.compile(r"^(.*)\.v(\d+)\.md$")


def split_prompt_ref(ref: str) -> tuple[str, int | None]:
    """`rewrite/step.v1.md` -> (id, version); unversioned -> (stem, None)."""
    match = _PROMPT_REF_RE.match(ref)
    if match:
        return match.group(1), int(match.group(2))
    stem = ref[:-3] if ref.endswith(".md") else ref
    return stem, None


def resolve_output_model(
    output_model: type[BaseModel] | None, card: AgentCard
) -> type[BaseModel]:
    """Subclass attribute first, else import the card's dotted path."""
    if output_model is not None:
        return output_model
    module_name, dot, attr = card.output_model.rpartition(".")
    if not dot:
        raise ConfigError(
            f"agent {card.name!r} output_model {card.output_model!r}"
            " is not a dotted path"
        )
    try:
        module = importlib.import_module(module_name)
        resolved = getattr(module, attr)
    except (ImportError, AttributeError) as exc:
        raise ConfigError(
            f"agent {card.name!r} output_model {card.output_model!r}"
            f" cannot be imported: {exc}"
        ) from exc
    if not isinstance(resolved, type) or not issubclass(resolved, BaseModel):
        raise ConfigError(
            f"agent {card.name!r} output_model {card.output_model!r}"
            " is not a BaseModel subclass"
        )
    return resolved


def render_system_text(prompts_dir: str | Path, card: AgentCard) -> str:
    """Render the card's system prompt (takes no variables in P03)."""
    prompt_id, version = split_prompt_ref(card.prompts.system)
    template = prompt_loader.load_prompt(prompts_dir, prompt_id, version)
    return template.render({})


def pack_for_call(ctx: AgentContext, system_text: str) -> ContextPack:
    """Caller pack re-rooted at the card's system prompt (16 §2)."""
    role = ctx.context_pack.system_role.strip()
    combined = f"{system_text}\n\n{role}" if role else system_text
    return ContextPack(
        task=ctx.context_pack.task,
        system_role=combined,
        pieces=list(ctx.context_pack.pieces),
    )
