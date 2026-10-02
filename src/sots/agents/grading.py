"""Grader stub interface for the agent GRADE hook (P03 T03.015, 16 §2).

BaseAgent calls `regeneration_loop` when the card names a rubric; P14
implements the real Quality Gate behind this protocol. Provisional by design:
the signature is fixed now so agents can be written against it.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class GradeDecision(BaseModel):
    """Outcome of one grading pass (provisional; P14 extends it)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    output: dict[str, Any]
    grade: float
    attempts: int
    passed: bool


class Grader(Protocol):
    """What the P14 Quality Gate implements (stub interface for P03)."""

    async def regeneration_loop(
        self,
        output: dict[str, Any],
        rubric: str,
        *,
        agent: str,
        run_id: str,
    ) -> GradeDecision:
        """Grade `output` against `rubric`, regenerating until pass/limit."""
        ...
