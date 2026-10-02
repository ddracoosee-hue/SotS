# SotS — The Subject of the Self

SotS is a terminal-based research, fact-checking, rewriting,
audience-testing, and legal-review system for the author's self-help /
reflective book for adult readers: *The Subject of the Self*.

## Setup

```powershell
uv sync
uv run sots init
uv run sots doctor
```

## Docs

Start at [MUSE_START_HERE.md](MUSE_START_HERE.md), then read the blueprint
in its reading order and work the tasks in `tasks/` in numeric order.

## Note for the author (keep visible)

> **Recheck & Reason is available whenever you want it.** Run `sots reason` (or press the
> TUI button) to have the Intent Keepers re-examine the book's structure from the
> psychological perspective of what you're trying to communicate, and the Counter-Council
> challenge the ideas. It never runs on its own. SotS reminds you when enough has changed to
> make a recheck worthwhile.
>
> **Voice Lab:** you can add any of your writing to `profile/voice_corpus/` at any time (the
> README there explains how). Every addition sharpens the voice model, and every voice check
> scales with it.
