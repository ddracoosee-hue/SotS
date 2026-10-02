# SotS build log

date | phase | status | note
-----|-------|--------|------
2026-09-29 | P00 | done | Skeleton: project files, folder tree, 12 configs, core modules, CLI stubs; ruff+pyright+pytest green (35 tests).
2026-09-29 | P01 | done | Models + storage: all model groups, SQLite schema/migrations, typed repo, idempotent save, atomic files, arch lint guard; ruff+pyright+pytest green (196 tests incl. vault).
2026-09-29 | OI-42 | done | Obsidian vault mirror (author-approved): `sots vault init/sync/status` rebuild `data/vault/` (Book Index, Chapters, Anchors, Messages, Motifs, Architecture) from `profile/` with wikilinked cross-chapter context; idempotent, author sections preserved, never deletes.
2026-09-29 | OI-42b | done | Vault phase 2: Book Dashboard (protocols/hotspots/coverage), pipeline-state sections from SQLite chapter_state, `sots vault digest` margin-note collection; ruff+pyright+pytest green (210 tests).
2026-09-29 | P02 | done | Providers: fake/local/muse adapters, routing+fallback, prompt loader, 9-step structured calls, cache, budget tree, call log, context packs (64 tasks), test-providers/cost CLI; ruff+pyright+pytest green (275 tests).
2026-09-29 | P03 | done | Agent runtime: BaseAgent 7-step lifecycle, cards/registry, Tool protocol + 11 tools, F01–F20, events bus, doctor/stop CLI wired; ruff+pyright+pytest green (425 tests).
2026-09-29 | P04 | done | Profile (loader/hash/interview/check CLI) + ingest (4-format loaders, normalize, pipeline, paste, supplements index, inbox invariant); ruff+pyright+pytest green (447 tests).
2026-09-29 | P04A | done | Book foundation: models/loader/anchors/architecture/versioning, brief parser + parse/check CLI, F1-F6 cards + R-FOUND-01, dictation keying, block_map, anchor tagging, provenance markers+cues, manuscript verify (ch01 sha ok), dictation coverage, protocol-load/repetition/arc checks (ch04/ch06/ch07/ch11 conflicts frozen); ruff+pyright+pytest green (489 tests).
2026-09-29 | P05 | done | Segment: sentence splitter (20 tricky), paragraph-first chunker + overlap, extract_units/summarize prompts, concurrency-limited extractor, rapidfuzz offset repair, coverage backstop (NARRATIVE_DEVICE), cross-chunk dedup, resumable stage, summary tree (1/7/8/9/65 shapes), offset_integrity invariant, 3 fixtures + integration; ruff+pyright+pytest green (511 tests).
2026-09-29 | P06 | done | Classify: safety scan (batches of 20, non-blocking notice), verbatim decision-table prompt + 7 examples, packed classifier with consistency retry, 4 code rules, embedded children (depth-1 FACTUAL), review queue + relabel (author wins), resumable stage, review CLI, doc stats, child-span integrity; ruff+pyright+pytest green (527 tests).
