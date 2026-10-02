"""Obsidian-vault mirror of the Book Foundation (OI-42).

The vault is a folder of plain Markdown notes with YAML frontmatter and
`[[wikilinks]]` that Obsidian opens directly. It mirrors `profile/` so chapter
context and whole-book threads stay navigable across chapters:

- `Book Index.md`: map of content (reading order, phases, motifs, messages)
- `Book Dashboard.md`: whole-book numbers (protocols, hotspots, coverage)
- `Author Notes Digest.md`: margin notes collected from across the vault
- `Chapters/`: one note per chapter with its messages, anchors, and threads
- `Anchors/`: one note per anchor with cross-chapter reuse backlinks
- `Messages/`: one note per book/chapter message
- `Motifs/`: one note per recurring-motif serial
- `Architecture/`: reading order, phases, arc, dependencies

Sync is idempotent and never deletes: managed sections are regenerated inside
markers, author-written sections are preserved byte-for-byte (R-DATA-05).
"""

from __future__ import annotations
