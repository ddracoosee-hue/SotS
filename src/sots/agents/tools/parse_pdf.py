"""PDF text extraction by page range via pypdf (P03 T03.024, 16 §3).

Reads a local PDF (fetched pages land in the fetch cache) and returns text
for the requested 1-based page range. Capped at 30 pages per call (F15).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from sots.agents.tools.base import ToolContext, register_tool
from sots.models.agents import Observation

MAX_PAGES = 30


def parse_pdf(path: str | Path, page_start: int = 1, page_end: int | None = None) -> dict:
    """Extract text for pages [page_start, page_end] (1-based, inclusive)."""
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise ValueError(f"PDF not found: {pdf_path}")
    if page_start < 1:
        raise ValueError("page_start must be >= 1")
    try:
        reader = PdfReader(str(pdf_path))
        total = len(reader.pages)
    except (PdfReadError, OSError) as exc:
        raise ValueError(f"cannot read PDF {pdf_path}: {exc}") from exc
    last = total if page_end is None else min(page_end, total)
    if last < page_start:
        raise ValueError(f"page range {page_start}-{page_end} exceeds {total} pages")
    if last - page_start + 1 > MAX_PAGES:
        last = page_start + MAX_PAGES - 1
        capped = True
    else:
        capped = False
    texts = [(reader.pages[i].extract_text() or "") for i in range(page_start - 1, last)]
    return {
        "path": str(pdf_path),
        "pages": total,
        "page_start": page_start,
        "page_end": last,
        "capped": capped,
        "text": "\n\n".join(texts),
    }


class ParsePdfArgs(BaseModel):
    """Local PDF path plus a 1-based page range."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    page_start: int = 1
    page_end: int | None = None


class ParsePdfTool:
    """`parse_pdf`: pypdf text by page range (16 §3)."""

    name = "parse_pdf"
    internet = False
    args_model = ParsePdfArgs

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, ParsePdfArgs)
        _ = ctx
        try:
            result = parse_pdf(args.path, args.page_start, args.page_end)
        except ValueError as exc:
            return Observation(tool=self.name, ok=False, content=f"error: {exc}", truncated=False)
        content = json.dumps(result)
        return Observation(
            tool=self.name, ok=True, content=content, truncated=result["capped"]
        )


register_tool(ParsePdfTool())
