"""Agent class registry (P03 T03.016, 16 §2).

Agent classes register via `@register_agent("card_name")`; `get_agent`
returns the class plus its validated card. Cards come from `cards.load_cards`
so the registry never sees an unvalidated card.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sots.errors import ConfigError
from sots.models.agents import AgentCard

if TYPE_CHECKING:
    from sots.agents.base import BaseAgent

_CLASSES: dict[str, type[BaseAgent]] = {}


def register_agent(name: str):  # type: ignore[no-untyped-def]
    """Class decorator registering an agent implementation under a card name."""

    def _register(cls):  # type: ignore[no-untyped-def]
        if name in _CLASSES:
            raise ValueError(f"agent {name!r} is already registered")
        _CLASSES[name] = cls
        return cls

    return _register


def get_agent(name: str, cards: dict[str, AgentCard]) -> tuple[type[BaseAgent], AgentCard]:
    """The (class, card) pair for an agent; unknown names raise ConfigError."""
    try:
        cls = _CLASSES[name]
    except KeyError as exc:
        raise ConfigError(f"agent {name!r} has no registered class") from exc
    try:
        card = cards[name]
    except KeyError as exc:
        raise ConfigError(f"agent {name!r} has no loaded card") from exc
    return cls, card


def registered_agents() -> dict[str, type[BaseAgent]]:
    """Snapshot of the class registry."""
    return dict(_CLASSES)


def clear_registry() -> None:
    """Empty the class registry (tests only)."""
    _CLASSES.clear()
