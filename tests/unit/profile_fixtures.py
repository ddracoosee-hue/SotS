"""Shared profile fixtures for P04 tests (not collected: no test_ prefix)."""

from __future__ import annotations

from pathlib import Path

AUTHOR_MD = """# Author Profile

## Name or Pen Name

Caleb Crouch

## Background

Philosopher and writer.

## Why This Book

To help people think.

## Lived Experience Areas

- addiction and recovery
- rehab

## Sensitive Topics

- family health

## Values

- truth over consensus

## Known Biases (self-reported)

- I trust stories over statistics
"""

BOOK_MD = """# Book Profile

## Working Title

The Subject of the Self

## Genre

self_help_reflective

## Premise

Attention is captured by design.

## Target Reader

Adults who think.

## Promise to the Reader

Clarity and agency.

## Tone Goals

- warm and direct

## Out of Scope

- clinical diagnosis

## Media Exclusions

- reality-TV retellings
"""

FLAT_MESSAGES = """messages:
  - {id: M1, level: book, chapter_id: null, statement: "book msg", priority: 1}
  - {id: C1.1, level: chapter, chapter_id: ch01, statement: "ch msg", priority: 2}
"""

NESTED_MESSAGES = """status: draft
version: 0
book:
  - {id: M1, priority: 1, statement: "book msg"}
chapters:
  ch01:
    - {id: C1.1, priority: 1, statement: "ch msg", book: [M1]}
"""

MANIFEST = """version: 1
samples:
  - {id: s1, path: final/a.md, register: final}
  - {id: s2, path: final/b.md, register: drafts}
  - {id: s3, path: final/c.md, register: spoken}
"""


def build_full_profile(root: Path) -> Path:
    """A complete, valid profile tree under `root/profile`."""
    profile = root / "profile"
    (profile / "chapters").mkdir(parents=True)
    (profile / "voice_corpus" / "final").mkdir(parents=True)
    (profile / "author.md").write_text(AUTHOR_MD, encoding="utf-8")
    (profile / "book.md").write_text(BOOK_MD, encoding="utf-8")
    (profile / "messages.yaml").write_text(FLAT_MESSAGES, encoding="utf-8")
    (profile / "voice_corpus" / "manifest.yaml").write_text(MANIFEST, encoding="utf-8")
    (profile / "chapters" / "ch01_brief.md").write_text("# brief", encoding="utf-8")
    for name in ("a.md", "b.md", "c.md"):
        (profile / "voice_corpus" / "final" / name).write_text("sample", encoding="utf-8")
    return profile
