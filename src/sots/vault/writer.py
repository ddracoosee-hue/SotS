"""Note rendering and atomic writes with author-section preservation (OI-42).

Every managed note has the same shape:

```markdown
---
<yaml frontmatter>
---

<!-- SOTS:GENERATED:START -->
<generated body, rebuilt on every sync>
<!-- SOTS:GENERATED:END -->

## Author notes

_<author's own text, never touched by sync>
```

Re-sync replaces only the frontmatter and the generated block. Everything
outside them (author notes, extra sections) is preserved byte-for-byte, and
sync never deletes files (R-DATA-05).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from sots.models.vault import VaultNote
from sots.storage.files import atomic_write_text, ensure_dir

GENERATED_START = "<!-- SOTS:GENERATED:START -->"
GENERATED_END = "<!-- SOTS:GENERATED:END -->"
DEFAULT_AUTHOR_HEADING = "## Author notes"
AUTHOR_PLACEHOLDER = "_Author space: SotS never edits below this line._"

WriteOutcome = Literal["created", "updated", "unchanged"]


def dump_frontmatter(frontmatter: dict[str, Any]) -> str:
    """Render a frontmatter dict as `---\\n<yaml>---\\n` (stable key order)."""
    body = yaml.safe_dump(
        frontmatter, sort_keys=True, allow_unicode=True, default_flow_style=False
    )
    return f"---\n{body}---\n"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split `(frontmatter, body)`; missing/invalid frontmatter yields `({}, text)`."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text
    lines = text.splitlines(keepends=True)
    for end in range(1, len(lines)):
        if lines[end].strip() in ("---", "..."):
            raw = "".join(lines[1:end])
            try:
                data = yaml.safe_load(raw) or {}
            except yaml.YAMLError:
                return {}, text
            if not isinstance(data, dict):
                return {}, text
            return data, "".join(lines[end + 1 :])
    return {}, text


def extract_author_section(
    existing: str | None, author_heading: str = DEFAULT_AUTHOR_HEADING
) -> str:
    """Return the author's own section from an existing note ("" when absent).

    The author owns everything from `author_heading` to end-of-file, plus any
    text outside the generated markers that is not frontmatter. Both are
    preserved verbatim across syncs.
    """
    if not existing:
        return ""
    _, body = split_frontmatter(existing)
    heading_at = body.find(author_heading)
    if heading_at >= 0:
        return body[heading_at:].rstrip() + "\n"
    # No author heading: keep any non-generated remainder (older/alien notes).
    remainder = body
    start_at = remainder.find(GENERATED_START)
    end_at = remainder.find(GENERATED_END)
    if start_at >= 0 and end_at > start_at:
        remainder = remainder[:start_at] + remainder[end_at + len(GENERATED_END) :]
    remainder = remainder.strip()
    if not remainder:
        return ""
    return f"{author_heading}\n\n{remainder}\n"


def build_note_text(
    note: VaultNote,
    existing: str | None = None,
    author_heading: str = DEFAULT_AUTHOR_HEADING,
) -> str:
    """Render a full note, preserving the author's section from `existing`."""
    author_section = extract_author_section(existing, author_heading)
    if not author_section:
        author_section = f"{author_heading}\n\n{AUTHOR_PLACEHOLDER}\n"
    generated = note.generated_body.rstrip() + "\n"
    return (
        f"{dump_frontmatter(note.frontmatter)}\n"
        f"{GENERATED_START}\n"
        f"{generated}"
        f"{GENERATED_END}\n"
        f"\n{author_section}"
    )


def write_note(
    vault_root: str | Path,
    note: VaultNote,
    author_heading: str = DEFAULT_AUTHOR_HEADING,
) -> WriteOutcome:
    """Atomically write one note; return created/updated/unchanged (F07)."""
    target = Path(vault_root) / note.rel_path
    ensure_dir(target.parent)
    existing = target.read_text(encoding="utf-8") if target.is_file() else None
    rendered = build_note_text(note, existing, author_heading)
    if existing == rendered:
        return "unchanged"
    atomic_write_text(target, rendered)
    return "created" if existing is None else "updated"


def write_static(
    vault_root: str | Path, rel_path: str, content: str
) -> WriteOutcome:
    """Atomically write unmanaged scaffolding (README, app.json); same outcomes."""
    target = Path(vault_root) / rel_path
    ensure_dir(target.parent)
    existing = target.read_text(encoding="utf-8") if target.is_file() else None
    if existing == content:
        return "unchanged"
    atomic_write_text(target, content)
    return "created" if existing is None else "updated"
