"""Scratchpad rendering and observation intake (W0 split of agents/base.py)."""

from __future__ import annotations

from typing import Any

from sots.agents.failsafes.f13_injection import strip_injections
from sots.agents.failsafes.f15_size import cap_text
from sots.models.agents import Observation


def render_scratchpad(entries: list[dict[str, Any]]) -> str:
    """Observations wrapped as data (T03.011, R-EXP-04)."""
    blocks = [
        f"<observation tool=\"{entry['tool']}\">\n"
        f"{entry['content']}\n</observation>"
        for entry in entries
    ]
    return "\n\n".join(blocks)


def post_observation(
    observation: Observation,
    *,
    injection_patterns: list[str],
    max_chars: int,
) -> dict[str, Any]:
    """F13 strip + F15 cap; returns the scratchpad entry (T03.011)."""
    cleaned, _hits = strip_injections(observation.content, injection_patterns)
    kept, _note = cap_text(
        cleaned, max_chars, f"observation:{observation.tool}"
    )
    return {"tool": observation.tool, "content": kept, "truncated": observation.truncated}
