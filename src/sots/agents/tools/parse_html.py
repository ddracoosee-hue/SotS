"""HTML → structured text via stdlib html.parser (P03 T03.023, 16 §3).

Extracts headings, paragraphs, list items, and tables into readable sections.
Output is capped at 20k chars with an explicit truncation note (F15).
"""

from __future__ import annotations

from html.parser import HTMLParser

from pydantic import BaseModel, ConfigDict

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation

MAX_CHARS = 20000
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg", "head"})
_HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._text: list[str] = []
        self._skip_depth = 0
        self._in_table = 0
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False
        self._table_rows: list[list[str]] = []
        self._list_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        _ = attrs
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "table":
            self._flush_text()
            self._in_table += 1
            self._table_rows = []
        elif tag == "tr" and self._in_table:
            self._row = []
        elif tag in ("td", "th") and self._in_table:
            self._cell = []
            self._in_cell = True
        elif tag in ("ul", "ol"):
            self._flush_text()
            self._list_depth += 1
        elif tag == "li":
            self._flush_text()
            self._text.append("  " * max(0, self._list_depth - 1) + "- ")
        elif tag == "br":
            self._text.append("\n")
        elif tag in _HEADING_TAGS or tag == "p":
            self._flush_text()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "table":
            self._in_table = max(0, self._in_table - 1)
            if not self._in_table and self._table_rows:
                self.blocks.append(_format_table(self._table_rows))
                self._table_rows = []
        elif tag == "tr" and self._in_table:
            self._table_rows.append(self._row)
            self._row = []
        elif tag in ("td", "th") and self._in_table:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = []
            self._in_cell = False
        elif tag in ("ul", "ol"):
            self._flush_text()
            self._list_depth = max(0, self._list_depth - 1)
        elif tag in _HEADING_TAGS:
            text = " ".join("".join(self._text).split())
            self._text = []
            if text:
                self.blocks.append(f"{_HEADING_TAGS[tag]} {text}")
        elif tag in ("p", "li", "div", "section", "article"):
            self._flush_text()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_cell:
            self._cell.append(data)
        else:
            self._text.append(data)

    def _flush_text(self) -> None:
        text = " ".join("".join(self._text).split())
        self._text = []
        if text:
            self.blocks.append(text)


def _format_table(rows: list[list[str]]) -> str:
    width = max((len(row) for row in rows), default=0)
    lines = [" | ".join(row + [""] * (width - len(row))) for row in rows if any(row)]
    return "[table]\n" + "\n".join(lines) if lines else ""


def parse_html(html: str, *, max_chars: int = MAX_CHARS) -> tuple[str, bool]:
    """HTML to structured text; returns (text, truncated)."""
    parser = _Extractor()
    parser.feed(html)
    parser.close()
    parser._flush_text()
    text = "\n\n".join(block for block in parser.blocks if block)
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars] + f"\n\n[truncated: showing {max_chars} of {len(text)} chars]", True


class ParseHtmlArgs(BaseModel):
    """Inline HTML to parse."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    html: str


class ParseHtmlTool:
    """`parse_html`: headings, paragraphs, and tables (16 §3)."""

    name = "parse_html"
    internet = False
    args_model = ParseHtmlArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, ParseHtmlArgs)
        _ = ctx
        text, truncated = parse_html(args.html)
        return Observation(tool=self.name, ok=True, content=text, truncated=truncated)


register_tool(ParseHtmlTool())
