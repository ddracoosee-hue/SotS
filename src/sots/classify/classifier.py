"""Per-unit classification (P06 T06.003, 05 §3.2).

One `classify.unit` call with a real context pack (pieces 1, 2, 3, 7 plus
the F1/F2 foundation prefix). Inconsistent output retries once with the
error list; a second failure returns None (FAILED) instead of guessing.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from sots.classify.consistency import ClassificationOut, validate_consistency
from sots.config import Settings
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextSources, build
from sots.providers.router import RoutingConfig, resolve
from sots.providers.structured import call_structured
from sots.storage.db import Connection

#: Standalone budget for one classification (short in, short out).
CLASSIFY_BUDGET_TOKENS = 20_000
#: Classifications are small; the routed window only scales piece budgets.
DEFAULT_CONTEXT_WINDOW = 32000


async def classify_unit(
    unit_id: str,
    unit_text: str,
    *,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    sources: ContextSources | None = None,
    initial_notes: str = "",
) -> ClassificationOut | None:
    """Classify one unit; None when two attempts both fail validation."""
    route = resolve("classify.unit", routing=routing, registry=providers)
    provider = providers[route.provider]
    pack = build(
        "classify.unit", sources or ContextSources(),
        budgets=settings.context.budgets,
        context_window=getattr(provider, "context_window", DEFAULT_CONTEXT_WINDOW),
        counter=provider.count_tokens,
    )
    notes = initial_notes
    for _ in range(2):
        out = await call_structured(
            "classify.unit", "classify/classify_unit",
            {"unit_id": unit_id, "unit_text": unit_text, "retry_notes": notes},
            ClassificationOut, pack, run_id, conn=conn, settings=settings,
            routing=routing, registry=providers,
            budget=BudgetNode(f"classify:{unit_id}", CLASSIFY_BUDGET_TOKENS),
            prompts_dir=prompts_dir, prompt_version=1,
        )
        errors = validate_consistency(out)
        if not errors:
            return out
        notes = "Previous attempt failed validation:\n" + "\n".join(
            f"- {error}" for error in errors
        )
    return None
