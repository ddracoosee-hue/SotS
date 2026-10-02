"""Static vault README text (W0 split of vault/notes.py)."""

from __future__ import annotations


def build_vault_readme() -> str:
    """Static vault README: how the mirror works and what is safe to edit."""
    return """# SotS Vault

An Obsidian vault mirroring the Book Foundation (`profile/`). Open this folder
in Obsidian to navigate chapters, anchors, messages, and motif threads.

- **Start at [[Book Index]].** It links the reading order, phases, and threads.
- **[[Book Dashboard]]** shows whole-book numbers: per-chapter counts, the full
  protocol inventory, reuse hotspots, and message coverage.
- Notes under `Chapters/`, `Anchors/`, `Messages/`, `Motifs/`, `Architecture/`
  are **managed**: `sots vault sync` rebuilds everything between the
  `SOTS:GENERATED` markers.
- **Your space is safe.** Everything under `## Author notes` (and any note you
  create yourself) is never touched or deleted by sync. `sots vault digest`
  collects your margin notes into [[Author Notes Digest]].
- The vault mirrors context; it never edits `profile/` (R-FOUND-02). Change the
  foundation in `profile/` (or the TUI), then re-run `sots vault sync`.

```powershell
uv run sots vault sync     # rebuild managed notes from profile/
uv run sots vault status   # show which foundation files changed since sync
uv run sots vault digest   # collect your margin notes into one digest note
```
"""
