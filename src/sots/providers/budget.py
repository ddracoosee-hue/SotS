"""Token/cost budgets as a reserve/commit/release tree (P02 T02.015-T02.016).

`settings.budget.max_tokens_per_run` (+ optional `max_cost_per_run`) roots the
tree; orchestrators carve run → act → team → agent slices with `new_child`.
Reserving checks the slice and every ancestor, so a nested slice exhausts
without touching its siblings; at 80% a warning is logged once per node, and
at 100% `reserve()` raises `BudgetExceededError` (04 §6).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from sots.config import ContextBudgets, Settings
from sots.errors import BudgetExceededError
from sots.providers import prompts as prompt_loader

logger = logging.getLogger(__name__)

WARN_FRACTION = 0.8


class BudgetNode:
    """One budget slice; the root is the run budget (04 §6)."""

    def __init__(
        self,
        name: str,
        max_tokens: int | None,
        max_cost: float | None = None,
        parent: BudgetNode | None = None,
    ) -> None:
        self.name = name
        self.max_tokens = max_tokens
        self.max_cost = max_cost
        self.parent = parent
        self.used_tokens = 0
        self.reserved_tokens = 0
        self.used_cost = 0.0
        self.reserved_cost = 0.0
        self.children: dict[str, BudgetNode] = {}
        self._warned_tokens = False
        self._warned_cost = False

    def new_child(
        self, name: str, max_tokens: int | None, max_cost: float | None = None
    ) -> BudgetNode:
        """Carve a nested slice (act/team/agent); names are unique per parent."""
        if name in self.children:
            raise ValueError(f"budget child {name!r} already exists under {self.name!r}")
        child = BudgetNode(name, max_tokens, max_cost, parent=self)
        self.children[name] = child
        return child

    def _chain(self) -> list[BudgetNode]:
        chain: list[BudgetNode] = []
        node: BudgetNode | None = self
        while node is not None:
            chain.append(node)
            node = node.parent
        return chain

    def path(self) -> str:
        """Dotted slice path for errors and logs (`run.act1.verify`)."""
        names = [node.name for node in reversed(self._chain())]
        return ".".join(names)

    def reserve(self, tokens: int, est_cost: float = 0.0) -> Reservation:
        """Hold budget for one call; raises BudgetExceededError at 100%."""
        if tokens < 0 or est_cost < 0:
            raise ValueError("cannot reserve negative budget")
        for node in self._chain():
            tokens_after = node.used_tokens + node.reserved_tokens + tokens
            if node.max_tokens is not None and tokens_after > node.max_tokens:
                raise BudgetExceededError(
                    f"token budget exhausted at slice '{node.path()}' "
                    f"({tokens_after - tokens}/{node.max_tokens})"
                )
            cost_after = node.used_cost + node.reserved_cost + est_cost
            if node.max_cost is not None and cost_after > node.max_cost:
                raise BudgetExceededError(
                    f"cost budget exhausted at slice '{node.path()}' "
                    f"({cost_after - est_cost:.4f}/{node.max_cost:.4f})"
                )
        for node in self._chain():
            node.reserved_tokens += tokens
            node.reserved_cost += est_cost
            node._maybe_warn()
        return Reservation(self._chain(), tokens, est_cost)

    def _maybe_warn(self) -> None:
        if (
            self.max_tokens
            and not self._warned_tokens
            and (self.used_tokens + self.reserved_tokens) / self.max_tokens >= WARN_FRACTION
        ):
            self._warned_tokens = True
            logger.warning("token budget 80%% used at slice '%s'", self.path())
        if (
            self.max_cost
            and not self._warned_cost
            and (self.used_cost + self.reserved_cost) / self.max_cost >= WARN_FRACTION
        ):
            self._warned_cost = True
            logger.warning("cost budget 80%% used at slice '%s'", self.path())

    def usage(self) -> dict[str, Any]:
        """Snapshot for reports and the TUI (04 §6)."""
        return {
            "path": self.path(),
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "reserved_tokens": self.reserved_tokens,
            "max_cost": self.max_cost,
            "used_cost": self.used_cost,
            "reserved_cost": self.reserved_cost,
        }


class Reservation:
    """Held budget for one call; `commit()` records actuals, `release()` frees."""

    def __init__(self, chain: list[BudgetNode], tokens: int, est_cost: float) -> None:
        self._chain = chain
        self._tokens = tokens
        self._est_cost = est_cost
        self._active = True

    @property
    def active(self) -> bool:
        """True until commit()/release() settles the reservation."""
        return self._active

    def _close(self) -> list[BudgetNode]:
        if not self._active:
            raise ValueError("reservation already settled")
        self._active = False
        for node in self._chain:
            node.reserved_tokens -= self._tokens
            node.reserved_cost -= self._est_cost
        return self._chain

    def commit(self, actual_tokens: int, actual_cost: float = 0.0) -> None:
        """Record what the call really spent; unused reservation is freed."""
        if actual_tokens < 0 or actual_cost < 0:
            raise ValueError("cannot commit negative usage")
        for node in self._close():
            node.used_tokens += actual_tokens
            node.used_cost += actual_cost

    def release(self) -> None:
        """Free a reservation the call never used (cache hit, failure)."""
        self._close()


def create_run_budget(settings: Settings) -> BudgetNode:
    """Root budget slice from `settings.budget` (04 §6)."""
    return BudgetNode("run", settings.budget.max_tokens_per_run, settings.budget.max_cost_per_run)


def compute_cost(
    settings: Settings, provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """Cost estimate from the settings price table (04 §6); unknown → 0.0."""
    _ = model
    prices = settings.providers
    if provider == "local":
        pin, pout = prices.local.price_input_per_1k, prices.local.price_output_per_1k
    elif provider == "muse":
        pin, pout = prices.muse.price_input_per_1k, prices.muse.price_output_per_1k
    else:
        return 0.0
    if pin is None or pout is None:
        return 0.0
    return input_tokens / 1000 * pin + output_tokens / 1000 * pout


def estimate(
    task: str,
    n_items: int,
    *,
    prompts_dir: str | Path,
    task_pieces: Mapping[str, list[str]],
    budgets: ContextBudgets,
    counter: Callable[[str], int],
    prompt_id: str | None = None,
    prompt_version: int | None = None,
) -> int:
    """Deterministic dry-run token estimate: prompt size + context budgets (T02.016).

    Per-item cost = prompt-file tokens + the summed piece budgets for the task;
    the total is per-item x n_items. No model is called.
    """
    pieces = task_pieces.get(task)
    if pieces is None:
        raise ValueError(f"no context pieces registered for task {task!r}")
    budget_map = budgets.model_dump()
    context_tokens = sum(int(budget_map[piece]) for piece in pieces)
    resolved_id = prompt_id or task.replace(".", "/")
    template = prompt_loader.load_prompt(prompts_dir, resolved_id, prompt_version)
    per_item = counter(template.body) + context_tokens
    if n_items < 0:
        raise ValueError("n_items must be >= 0")
    return math.ceil(per_item) * n_items
