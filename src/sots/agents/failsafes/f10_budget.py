"""F10 budget guard: per-invocation slices in the budget tree (P03 T03.049, 16 §5.1).

Each agent invocation gets a child slice (or a standalone root when no
parent is passed). BaseAgent reserves before every model call and commits
after; a BudgetExceededError stops that agent cleanly as `degraded` while
team siblings on their own slices continue.
"""

from __future__ import annotations

from sots.providers.budget import BudgetNode


def agent_slice(
    parent: BudgetNode | None,
    agent_name: str,
    max_tokens: int,
    max_cost: float | None = None,
) -> BudgetNode:
    """A child slice under `parent`, or a standalone root slice."""
    if parent is None:
        return BudgetNode(agent_name, max_tokens, max_cost)
    return parent.new_child(agent_name, max_tokens, max_cost)
