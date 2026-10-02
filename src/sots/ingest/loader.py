"""Format loaders: txt/md/docx/pdf to text (P04 T04.010, 05 Stage 1)."""

from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader

TEXT_SUFFIXES = frozenset({".txt", ".md"})
MIN_CHARS_PER_PAGE = 50
SCANNED_WARNING = "scanned PDF, OCR not supported"


class Extracted(BaseModel):
    """Extracted text plus non-fatal warnings (e.g. scanned PDFs)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    warnings: list[str]


def _read_text_bytes(raw: bytes) -> str:
    """UTF-8 with a cp1252 fallback (05 Stage 1)."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def extract_text(path: str | Path) -> Extracted:
    """Extract plain text from a .txt/.md/.docx/.pdf file (05 Stage 1)."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return Extracted(text=_read_text_bytes(source.read_bytes()), warnings=[])
    if suffix == ".docx":
        paragraphs = [para.text for para in DocxDocument(str(source)).paragraphs]
        return Extracted(text="\n\n".join(paragraphs), warnings=[])
    if suffix == ".pdf":
        pages = [(page.extract_text() or "") for page in PdfReader(str(source)).pages]
        chars = sum(len(page) for page in pages)
        warnings: list[str] = []
        per_page = chars / len(pages) if pages else 0
        if per_page < MIN_CHARS_PER_PAGE:
            warnings.append(SCANNED_WARNING)
        return Extracted(text="\n\n".join(pages), warnings=warnings)
    raise ValueError(f"unsupported ingest format: {suffix or '(none)'}")
