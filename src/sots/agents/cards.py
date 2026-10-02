"""Agent card loading + validation (P03 T03.001-T03.002, 16 §1, §5.2).

Every YAML card under `config/agents/` validates against `AgentCard`, and the
loader additionally checks: prompt files exist, the routing task exists, every
tool is registered, and the team's mandatory failsafes are included. Any
invalid card fails `sots doctor`, and the app will not start.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from sots.agents.tools.base import Tool
from sots.errors import ConfigError
from sots.models.agents import AgentCard
from sots.providers.router import RoutingConfig

BASE_MANDATORY: frozenset[str] = frozenset(
    {"F01", "F02", "F05", "F06", "F07", "F08", "F10", "F12", "F16", "F20"}
)
INTERNET_EXTRA: frozenset[str] = frozenset({"F03", "F13", "F14", "F15"})
MULTISTEP_EXTRA: frozenset[str] = frozenset({"F04", "F09"})

#: Known context cards (23 §3); the card field may only name these.
KNOWN_FOUNDATION_PIECES: frozenset[str] = frozenset({"F1", "F2", "F3", "F4", "F5", "F6"})

#: Teams whose output concerns the book's content (R-FOUND-01: need F1+F2).
CONTENT_TEAMS: frozenset[str] = frozenset({
    "fact_check", "media", "psyche", "narrative", "shadow", "rewrite_team_a",
    "rewrite_team_b", "audience_lab", "legal_chamber", "discovery",
    "quality_gate", "proposal_desk",
})


def cards_missing_foundation(cards: Mapping[str, AgentCard]) -> list[str]:
    """Content-team cards omitting F1 or F2 (R-FOUND-01; doctor warns)."""
    return sorted(
        name
        for name, card in cards.items()
        if card.team in CONTENT_TEAMS
        and not {"F1", "F2"}.issubset(set(card.foundation_pieces))
    )


def mandatory_failsafes(team: str, internet: bool, max_steps: int) -> frozenset[str]:
    """Required failsafe set from team + internet + max_steps (16 §5.2)."""
    required = set(BASE_MANDATORY)
    if internet:
        required |= INTERNET_EXTRA
    if max_steps > 1:
        required |= MULTISTEP_EXTRA
    if team == "legal_chamber":
        required.add("F09")
    if team.startswith("rewrite"):
        required.add("F11")
    return frozenset(required)


def load_cards(
    cards_dir: str | Path,
    *,
    prompts_dir: str | Path,
    routing: RoutingConfig,
    tools: Mapping[str, Tool[Any]],
) -> dict[str, AgentCard]:
    """Load + validate every `*.yaml` card; name -> card (T03.001)."""
    root = Path(cards_dir)
    if not root.is_dir():
        raise ConfigError(f"agent cards dir not found: {root}")
    cards: dict[str, AgentCard] = {}
    for path in sorted(root.rglob("*.yaml")):
        card = _load_one(path, prompts_dir=Path(prompts_dir), routing=routing, tools=tools)
        if card.name in cards:
            raise ConfigError(f"duplicate agent card name {card.name!r} in {path}")
        cards[card.name] = card
    return cards


def _load_one(
    path: Path,
    *,
    prompts_dir: Path,
    routing: RoutingConfig,
    tools: Mapping[str, Tool[Any]],
) -> AgentCard:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse agent card {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"agent card {path} must parse to a mapping")
    try:
        card = AgentCard.model_validate(raw)
    except ValueError as exc:
        raise ConfigError(f"invalid agent card {path}: {exc}") from exc
    if not card.name.replace("_", "").isalnum() or not card.name.islower():
        raise ConfigError(f"agent card {path} has a non-snake_case name {card.name!r}")
    _check_prompts(path, card, prompts_dir)
    if card.routing_task not in routing.tasks:
        raise ConfigError(
            f"agent card {path} names unknown routing task {card.routing_task!r}"
        )
    unknown_tools = [name for name in card.tools if name not in tools]
    if unknown_tools:
        raise ConfigError(
            f"agent card {path} names unregistered tools: {', '.join(unknown_tools)}"
        )
    missing = mandatory_failsafes(card.team, card.internet, card.limits.max_steps) - set(
        card.failsafes
    )
    if missing:
        raise ConfigError(
            f"agent card {path} is missing mandatory failsafes: {', '.join(sorted(missing))}"
        )
    unknown_pieces = sorted(set(card.foundation_pieces) - KNOWN_FOUNDATION_PIECES)
    if unknown_pieces:
        raise ConfigError(
            f"agent card {path} names unknown foundation pieces:"
            f" {', '.join(unknown_pieces)}"
        )
    return card


def _check_prompts(path: Path, card: AgentCard, prompts_dir: Path) -> None:
    missing = [
        filename
        for filename in (card.prompts.system, card.prompts.step)
        if not (prompts_dir / filename).is_file()
    ]
    if missing:
        raise ConfigError(
            f"agent card {path} references missing prompt files: {', '.join(missing)}"
        )


def card_to_dict(card: AgentCard) -> dict[str, Any]:
    """Card back to plain data (report/debug use)."""
    return card.model_dump(mode="json")
