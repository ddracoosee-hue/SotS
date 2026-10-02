# P04A — Book Foundation Layer

**Prerequisites:** P04. **Blueprint refs:** 23 (all), 01 §D4, 25 §1.
**Foundation files already present:** `profile/book.md`, `author.md`, `messages.yaml`,
`style_guide_seed.yaml`, `anchors.yaml`, `book_architecture.yaml`, `chapters/ch01–12_brief.md`,
`chapters/source/*.docx`. **Do not rewrite their content.** Build the code that loads, validates,
and serves them.

## Models + loading
- [x] **T04A.001** | `models/foundation.py` | DictationPrompt, BriefAnchor, Protocol, Block, ChapterBrief (23 §2); BookArchitecture (reading_order, phases, arc, motif_serials, brief_edits_required, alternatives); FoundationChange; EpistemicTier enum (25 §1). | Round-trip tests.
- [x] **T04A.002** | `foundation/loader.py` | Load every foundation file into a frozen `Foundation` object; validate ids (ch01–ch12), messages→book links, anchors' chapter prefixes, the architecture's reading_order (a permutation of the chapter ids). | Tests against the real profile files: loads with 0 errors.
- [x] **T04A.003** | `foundation/anchors.py` | Anchor Registry API: `by_chapter`, `by_type`, `reuse_hotspots`, `match_in_text(text) -> anchor_ids` (entity + keyword matching on names/titles/terms). | Tests: "Berridge", "Love Yourz", "chrēstos" (incl. "chrestos" without the macron) all match.
- [x] **T04A.004** | `foundation/architecture.py` | reading position ↔ chapter id; phase lookup; `arc_position(ch)`; `callback_label(ch)` ("Chapter N" in reading order); the motif-serial plan per chapter. | Tests.
- [x] **T04A.005** | `foundation/versioning.py` | A version per file (hash + the `version:` field); FoundationChange records; a run snapshot of the versions. | Tests.

## Brief Parser (replaces the provisional T04.006)
- [x] **T04A.010** | `prompts/foundation/parse_brief.v1.md` + `foundation/brief_parser.py` | LLM parse of `chNN_brief.md` → ChapterBrief; dictation prompt ids assigned as `chNN.B<block>.P<n>`; anchors linked to the anchors.yaml ids by fuzzy match; protocols extracted with their claimed grade/basis; appendix system prompt stored verbatim as data. | Tests with FakeProvider fixtures for ch01, ch05, ch11 (the three differently formatted briefs).
- [x] **T04A.011** | `foundation/brief_parser.py` | Validation: exactly 6 blocks; block 2 has old/new belief; block 5 has 3 protocols; block 6 has ≥ 3 journaling prompts; every brief anchor resolves or is reported as `unregistered_anchor` (→ proposed addition to anchors.yaml). | Tests.
- [x] **T04A.012** | `cli.py` | `sots foundation parse [chNN|all]` → writes `profile/chapters/chNN.yaml` (**only if absent**, or with `--overwrite` after a confirmation) + a diff report. | Test.
- [x] **T04A.013** | `cli.py` | `sots foundation check` → a validation table for every foundation file; used by `sots doctor`. | Test.
- [x] **T04A.014** | `foundation/brief_parser.py` | R-FOUND-04 guard: the appendix system prompt is stored in a field that no context pack or prompt template may inject (checked by a test that greps all rendered prompts in the integration suite). | Test.

## Context pieces F1–F6
- [x] **T04A.020** | `foundation/cards.py` | Builders for F1 Book Card, F2 Chapter Card, F3 Block Card, F4 Anchor Slice, F5 Voice Card, F6 Arc Position, within the budgets of 23 §3. | Tests: every card is within budget for all 12 chapters × 6 blocks.
- [x] **T04A.021** | `providers/context_pack.py` | Register F1–F6 as pieces; extend TASK_PIECES for every routing task (content tasks include F1+F2). | Test: R-FOUND-01 is enforced for content tasks.
- [x] **T04A.022** | `agents/cards.py` | The `foundation_pieces` field on AgentCard; doctor warns when a content agent omits F1/F2. | Test.

## Dictation keying (23 §5)
- [x] **T04A.030** | `ingest/dictation.py` | Parse the header/inline markers (`chapter:`, `block:`, `### ch03.B2.P1`, `[B2.P1]`) → keyed sections with offsets into the canonical text. | Tests on 5 marker styles + unmarked text.
- [x] **T04A.031** | `classify/block_map.py` + prompt | Map unmarked units to a block/prompt with the Block Cards (task `classify.block_map`). | FakeProvider test.
- [x] **T04A.032** | `classify/anchors_in_units.py` | Fill `unit.anchor_ids` via `match_in_text`. | Test.
- [x] **T04A.034** | `ingest/provenance_markers.py` + `classify/provenance.py` | Detect the author provenance markers (`[LIVE: …]`, `[SOURCE: …]`, `[BELIEF]`, `[EXPERIENCE]`, `[OPINION]`; plus the routing marker `[SPIRAL]` → `unit.serial = provocation_spiral`, 25 §7.1) and natural-language cues ("I believe", "what follows is my personal opinion", "according to") → `unit.author_provenance` + `source_ref`; low confidence → review queue (25 §7). | Tests on Ch1 passages: the §4 opinion paragraph → opinion; "I believe God exists" → belief; Casey Simpson → live_source. |
- [x] **T04A.035** | `foundation/manuscript.py` | Load author-final chapters (`profile/manuscript/`), verify sha256, register them as `author_final` sections, and expose them as the primary style exemplar + reference chapter. | Test: the Ch1 hash matches ch01_analysis.md. |
- [x] **T04A.033** | `reports/sections/dictation_coverage.py` | Per chapter: prompts answered / partial / missing; anchors used vs planned. | Snapshot test.

## Book-level checks (23 §7)
- [x] **T04A.040** | `foundation/protocol_load.py` | The Protocol Load Auditor's deterministic core: estimate the weekly minutes per protocol (LLM estimate + author override), cumulative load in reading order, concurrent "active" practices vs `book.protocol_budget`. | Tests with the 36 brief protocols (fixture).
- [x] **T04A.041** | `narrative/repetition.py` | The Repetition Manager: for each reuse hotspot, check each chapter's treatment (full vs callback) against the motif_serials plan. | Tests.
- [x] **T04A.042** | `shadow/arc_consistency.py` | Phase labels / "capstone / epilogue / climax / Chapter N of M" claims vs the architecture; forward references vs reading order. | A test detects the known ch06/ch07/ch08/ch04 conflicts.

## Phase close
- [x] **T04A.090** | — | All green; `sots foundation check` passes on the real profile; BUILD_LOG line. | Done.
