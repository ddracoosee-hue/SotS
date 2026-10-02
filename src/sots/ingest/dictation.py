"""Dictation keying: header/inline markers to keyed sections (P04A T04A.030, 23 §5).

Five marker styles plus unmarked text (which the LLM block-mapper keys in
T04A.031). Offsets index the canonical text; marker and header lines are
metadata, excluded from section bodies.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_HEADER_RE = re.compile(r"^(chapter|block|prompt)\s*:\s*(\S.*\S|\S)\s*$", re.IGNORECASE)
_FULL_MARKER_RE = re.compile(r"^###\s+(ch\d+\.B\d+\.P\d+)\s*$")
_SHORT_MARKER_RE = re.compile(r"^\[(B\d+\.P\d+)\]\s*$")
_CHAPTER_RE = re.compile(r"^ch\d+$")
_PROMPT_ID_RE = re.compile(r"^(ch\d+)\.(B\d+)\.(P\d+)$")


class KeyedSection(BaseModel):
    """One dictation section with offsets into the canonical text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chapter_id: str | None
    block: int | None
    prompt_id: str | None
    start_char: int
    end_char: int
    text: str


def _split_prompt(prompt_id: str) -> tuple[str, int] | None:
    match = _PROMPT_ID_RE.match(prompt_id.strip())
    if match is None:
        return None
    return match.group(1), int(match.group(2)[1:])


def parse_keyed_sections(
    text: str, *, default_chapter: str | None = None
) -> list[KeyedSection]:
    """Parse markers into sections (headers apply file-wide from the top)."""
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)

    chapter = default_chapter
    block: int | None = None
    prompt: str | None = None
    index = 0
    # File-top header: chapter:/block:/prompt: lines (+ blanks) only.
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        match = _HEADER_RE.match(stripped)
        if match is None:
            break
        key, value = match.group(1).lower(), match.group(2).strip()
        if key == "chapter" and _CHAPTER_RE.match(value):
            chapter = value
        elif key == "block" and value.isdigit():
            block = int(value)
        elif key == "prompt":
            split = _split_prompt(value)
            if split is not None:
                prompt = value
                chapter, block = split
        index += 1

    sections: list[KeyedSection] = []
    body: list[tuple[int, str]] = []

    def _flush() -> None:
        trimmed = [(off, line) for off, line in body]
        while trimmed and not trimmed[0][1].strip():
            trimmed.pop(0)
        body.clear()
        if not trimmed:
            return
        start = trimmed[0][0]
        content = "".join(line for _, line in trimmed).rstrip("\n")
        if content.strip():
            sections.append(KeyedSection(
                chapter_id=chapter, block=block, prompt_id=prompt,
                start_char=start, end_char=start + len(content), text=content,
            ))

    for line_no in range(index, len(lines)):
        line = lines[line_no]
        stripped = line.strip()
        full = _FULL_MARKER_RE.match(stripped)
        short = _SHORT_MARKER_RE.match(stripped)
        if full is not None:
            _flush()
            full_id: str = full.group(1)
            prompt = full_id
            split = _split_prompt(full_id)
            if split is not None:
                chapter, block = split
        elif short is not None and chapter is not None:
            _flush()
            prompt = f"{chapter}.{short.group(1)}"
            split = _split_prompt(prompt)
            if split is not None:
                block = split[1]
        else:
            body.append((offsets[line_no], line))
    _flush()
    # Markers are sticky to the next marker; unmarked sections stay None.
    return sections


def parse_keyed_file(
    path: str | Path, *, default_chapter: str | None = None
) -> list[KeyedSection]:
    """Parse a dictation file (convenience wrapper)."""
    return parse_keyed_sections(
        Path(path).read_text(encoding="utf-8"), default_chapter=default_chapter
    )
