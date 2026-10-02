"""Safe arithmetic/statistics over row columns (P03 T03.026, 16 §3-§4).

Numbers in reports are computed here, never by the LLM (16 §4). The evaluator
parses with `ast` and only allows numbers, `+ - * /`, parentheses, and the
whitelisted functions over named columns. Anything else — imports, attribute
access, lambdas, subscripts, calls outside the whitelist — is rejected.
"""

from __future__ import annotations

import ast
import json
import math
import statistics
from typing import Any

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values)


def _median(values: list[float]) -> float:
    return statistics.median(values)


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        raise ValueError("pct_change with a zero baseline")
    return (new - old) / old


def _ratio(top: float, bottom: float) -> float:
    if bottom == 0:
        raise ValueError("ratio with a zero denominator")
    return top / bottom


_FUNCTIONS: dict[str, Any] = {
    "mean": _mean,
    "median": _median,
    "sum": sum,
    "min": min,
    "max": max,
    "pct_change": _pct_change,
    "ratio": _ratio,
}


class ComputeArgs(BaseModel):
    """Expression plus the named columns it may reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    expression: str
    columns: dict[str, list[float]] = {}


def evaluate(expression: str, columns: dict[str, list[float]]) -> float:
    """Evaluate a whitelisted expression; anything else raises ValueError."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression: {exc}") from exc
    return _eval(tree.body, columns)


def _eval(node: ast.AST, columns: dict[str, list[float]]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, columns)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"only numbers are allowed, got {node.value!r}")
        return float(node.value)
    if isinstance(node, ast.Name):
        if node.id not in columns:
            raise ValueError(f"unknown column {node.id!r}")
        return [float(v) for v in columns[node.id]]
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise ValueError(f"operator {type(node.op).__name__} is not allowed")
        left, right = _eval(node.left, columns), _eval(node.right, columns)
        if isinstance(left, list) or isinstance(right, list):
            raise ValueError("arithmetic applies to scalars, not whole columns")
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ValueError("division by zero")
        return left / right
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARYOPS):
            raise ValueError(f"operator {type(node.op).__name__} is not allowed")
        value = _eval(node.operand, columns)
        if isinstance(value, list):
            raise ValueError("unary operators apply to scalars, not whole columns")
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
            raise ValueError("only whitelisted functions may be called")
        if node.keywords:
            raise ValueError("keyword arguments are not allowed")
        func = _FUNCTIONS[node.func.id]
        args = [_eval(arg, columns) for arg in node.args]
        if node.func.id in ("mean", "median", "sum", "min", "max"):
            if len(args) != 1 or not isinstance(args[0], list):
                raise ValueError(f"{node.func.id} takes exactly one column")
            if not args[0]:
                raise ValueError(f"{node.func.id} of an empty column")
            return float(func(args[0]))
        if len(args) != 2 or any(isinstance(a, list) for a in args):
            raise ValueError(f"{node.func.id} takes exactly two scalars")
        return float(func(args[0], args[1]))
    raise ValueError(f"{type(node).__name__} nodes are not allowed")


class ComputeTool:
    """`compute`: no eval(), ever (16 §3)."""

    name = "compute"
    internet = False
    args_model = ComputeArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, ComputeArgs)
        _ = ctx
        try:
            result = evaluate(args.expression, dict(args.columns))
        except ValueError as exc:
            return Observation(tool=self.name, ok=False, content=f"error: {exc}", truncated=False)
        if not math.isfinite(result):
            return Observation(
                tool=self.name, ok=False, content="error: non-finite result", truncated=False
            )
        payload = json.dumps({"expression": args.expression, "result": result})
        return Observation(tool=self.name, ok=True, content=payload, truncated=False)


register_tool(ComputeTool())
