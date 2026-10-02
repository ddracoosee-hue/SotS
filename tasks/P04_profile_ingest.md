# P04 — Profile + Ingest

**Prerequisites:** P03. **Blueprint refs:** 05 Stage 1, 03 §8, 04 §4, OI-01/10/11.

## Profile
- [x] **T04.001** | `profile/loader.py` | Load author.md, book.md, messages.yaml, chapters/*.md, and the voice_corpus manifest (`profile/voice_corpus/manifest.yaml`, 29; the corpus itself is loaded by P11A) → the typed models. Markdown files use `## Field` headings mapped to model fields. | Tests: full profile; partial profile → a list of the missing parts.
- [x] **T04.002** | `profile/loader.py` | `profile_hash()` over all profile files (used for cache invalidation of the Style Guide and context packs). | Test: a change in any file changes the hash.
- [x] **T04.003** | `profile/interview.py` | A guided interview (Typer prompts in the CLI; a TUI version in P22): asks the AuthorProfile + BookProfile fields one by one with examples; writes the markdown files; never overwrites without confirmation. | A test using an injected input stream.
- [x] **T04.004** | `profile/validate.py` | `profile check`: required fields, a messages.yaml schema, chapter ids consistent between briefs and messages, style samples ≥ 3 files (warn), reader_journey ids valid. | Tests.
- [x] **T04.005** | `cli.py` | Wire `sots profile interview|check`. | Manual + a unit test.
- [ ] ~~**T04.006**~~ SUPERSEDED by P04A T04A.010–014 (the real briefs have arrived). | `profile/chapter_brief_parser.py` | Parse free-form chapter briefs into ChapterBrief (keeping raw_brief). Fields not found → empty, plus a warning listing them. **Provisional until the author's briefs arrive (OI-01).** | Tests on 2 fixture briefs.

## Ingest
- [x] **T04.010** | `ingest/loader.py` | `.txt/.md` (UTF-8, cp1252 fallback), `.docx` (paragraphs joined by `\n\n`), `.pdf` (pypdf; scanned-PDF warning). | Tests on each format fixture with the same content → the same text after normalization.
- [x] **T04.011** | `ingest/normalize.py` | Line endings, NBSP, 3+ blank lines → 2. Never alters words. | A test asserting the word sequence is unchanged.
- [x] **T04.012** | `ingest/ingest.py` | sha256 → duplicate check → copy to the inbox → write the canonical .txt → a Document row. | Tests: byte-identical copy; duplicate detection.
- [x] **T04.013** | `ingest/ingest.py` | Pasted text support: save to `data/inbox/paste_<ts>.md`, then ingest as usual. | Test.
- [x] **T04.014** | `cli.py` | `sots ingest <path> [--chapter] [--title]` → prints the doc_id; handles duplicates with a prompt (default reuse). | Test.
- [x] **T04.015** | `ingest/supplements.py` | Index `supplements/` files (the same loaders) into a `supplement_docs` table with text + hash, used by the supplements fetcher (P07). | Test.
- [x] **T04.016** | `failsafes/f20_invariants.py` | Register invariant `raw_files_unchanged` over all inbox files. | Test: a modified inbox file → a violation.

## Phase close
- [x] **T04.090** | — | All green; BUILD_LOG line. | Done.
