"""Agent invocation context (W0 split of agents/base.py)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sots.models.agents import AgentCard, BudgetSlice
from sots.providers.context_pack import ContextPack


class AgentContext(BaseModel):
    """One agent invocation (16 §2). Built by the caller, consumed by run()."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    act: str
    card: AgentCard
    inputs: BaseModel
    context_pack: ContextPack
    budget: BudgetSlice
    checkpoint_key: str
