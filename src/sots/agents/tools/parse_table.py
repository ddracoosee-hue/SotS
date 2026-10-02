"""HTML table / CSV / JSON → typed rows (P03 T03.025, 16 §3).

Column values get inferred types: "1,234" → 1234, "12.5%" → 0.125, "—"/""
→ None (missing), otherwise float/int when the whole column parses, else str.
Capped at 2000 rows with an explicit note (F15).
"""

from __future__ import annotations

import csv
import io
import json
from html.parser import HTMLParser
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation

MAX_ROWS = 2000
MISSING_TOKENS = frozenset({"", "—", "-", "–", "n/a", "N/A", "null", "None"})  # noqa: RUF001


class _TableGrabber(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False
        self._in_table = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        _ = attrs
        if tag == "table":
            self._in_table += 1
            self._rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in ("td", "th") and self._in_table:
            self._cell = []
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._in_table = max(0, self._in_table - 1)
            if not self._in_table:
                self.tables.append(self._rows)
                self._rows = []
        elif tag == "tr" and self._in_table:
            self._rows.append(self._row)
            self._row = []
        elif tag in ("td", "th") and self._in_table:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = []
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_table and self._in_cell:
            self._cell.append(data)


def _to_number(token: str) -> int | float | str | None:
    """Infer one cell: numbers (with commas/percents) else the raw string."""
    text = token.strip()
    if text in MISSING_TOKENS:
        return None
    cleaned = text.replace(",", "").replace("\u00a0", "")
    is_percent = cleaned.endswith("%")
    if is_percent:
        cleaned = cleaned[:-1]
    try:
        number: int | float = int(cleaned)
    except ValueError:
        try:
            number = float(cleaned)
        except ValueError:
            return token
    if is_percent:
        number = number / 100
    return number


def _rows_from_html(data: str) -> list[list[str]]:
    grabber = _TableGrabber()
    grabber.feed(data)
    grabber.close()
    for table in grabber.tables:
        if table:
            return table
    raise ValueError("no HTML table found in the input")


def _rows_from_csv(data: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(data))
    return [row for row in reader if row]


def _rows_from_json(data: str) -> list[dict[str, Any]]:
    payload = json.loads(data)
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        payload = payload["rows"]
    if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
        raise ValueError("JSON tables must be a list of row objects")
    return payload


def parse_table(
    format: Literal["html", "csv", "json"], data: str, *, max_rows: int = MAX_ROWS
) -> dict[str, Any]:
    """Parse to {columns, rows, dtypes, truncated, note?} (never raises on shape)."""
    if format == "json":
        raw_rows = _rows_from_json(data)
        columns = list(raw_rows[0].keys()) if raw_rows else []
        typed = [
            {
                k: v
                if isinstance(v, (int, float)) and not isinstance(v, bool)
                else _to_number(str(v))
                for k, v in row.items()
            }
            for row in raw_rows
        ]
    else:
        grid = _rows_from_html(data) if format == "html" else _rows_from_csv(data)
        if not grid:
            raise ValueError(f"no rows found in the {format} input")
        columns = [cell if cell else f"col{i + 1}" for i, cell in enumerate(grid[0])]
        typed = []
        for grid_row in grid[1:]:
            padded = grid_row + [""] * (len(columns) - len(grid_row))
            pairs = zip(columns, padded, strict=False)
            typed.append({col: _to_number(cell) for col, cell in pairs})
    dtypes = {col: _dtype([row[col] for row in typed]) for col in columns}
    result: dict[str, Any] = {
        "columns": columns,
        "rows": typed,
        "dtypes": dtypes,
        "truncated": False,
    }
    if len(typed) > max_rows:
        result["rows"] = typed[:max_rows]
        result["truncated"] = True
        result["note"] = f"showing {max_rows} of {len(typed)} rows"
    return result


def _dtype(values: list[Any]) -> str:
    present = [v for v in values if v is not None]
    if not present:
        return "null"
    if all(isinstance(v, bool) for v in present):
        return "bool"
    if all(isinstance(v, int) and not isinstance(v, bool) for v in present):
        return "int"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return "float"
    return "str"


class ParseTableArgs(BaseModel):
    """Table format plus the raw table text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format: Literal["html", "csv", "json"]
    data: str


class ParseTableTool:
    """`parse_table`: rows with inferred numeric types (16 §3)."""

    name = "parse_table"
    internet = False
    args_model = ParseTableArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, ParseTableArgs)
        _ = ctx
        try:
            result = parse_table(args.format, args.data)
        except (ValueError, json.JSONDecodeError) as exc:
            return Observation(tool=self.name, ok=False, content=f"error: {exc}", truncated=False)
        return Observation(
            tool=self.name, ok=True, content=json.dumps(result),
            truncated=bool(result["truncated"]),
        )


register_tool(ParseTableTool())
