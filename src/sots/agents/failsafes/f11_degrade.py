"""F11 degraded mode: per-team degrade policies (P03 T03.050, 16 §5.1).

When a provider or tool is unavailable, agents degrade instead of failing:
rewrite teams degrade to "no change" rather than a bad change, fact-check
caps verdicts at MOSTLY_TRUE, audience work is marked low-confidence.
Everything degraded is labeled as such in reports.
"""

from __future__ import annotations

from typing import Any

#: Team -> degrade markers merged into the degraded payload.
DEGRADE_POLICIES: dict[str, dict[str, Any]] = {
    "rewrite_pass_a": {"degraded_mode": "no_change"},
    "rewrite_pass_b": {"degraded_mode": "no_change"},
    "fact_check": {"verdict_cap": "MOSTLY_TRUE"},
    "audience_lab": {"confidence": "low"},
}


def policy_for(team: str) -> dict[str, Any]:
    """Raw policy markers for a team ({} when the team has no policy)."""
    return dict(DEGRADE_POLICIES.get(team, {}))


def degrade(team: str, payload: dict[str, Any], reason: str) -> dict[str, Any]:
    """Apply the team's policy; the result is always labeled degraded."""
    degraded = dict(payload)
    degraded.update(policy_for(team))
    degraded["degraded"] = True
    degraded["degrade_reason"] = reason
    return degraded
