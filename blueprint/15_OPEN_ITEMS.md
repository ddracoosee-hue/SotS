# 15 — OPEN ITEMS

Muse: never guess these answers. Build around them, and append new questions at the bottom.

## A. Waiting on the author

| ID | Item | Blocks | Default until answered |
|---|---|---|---|
| OI-01 | ✅ **RESOLVED 2026-09-28**: all 12 chapter briefs received (`profile/chapters/`). Remaining: review the structured `chNN.yaml` produced by the Brief Parser. Formerly: **Chapter briefs** (all chapters) | `profile/chapters/`, `messages.yaml`, the final `ChapterBrief` model, parts of stage 8, the gold set | Stage 8 runs voice/flow only |
| OI-02 | 🟡 **DRAFT v0 in `profile/messages.yaml`**: refine with the author. **Core messages**: book-level and per chapter, with priorities (worked out together from the briefs) | stage 8 ledger, rubric `message_clarity`, TR-03, R-EXP-07 | the metrics are reported as "n/a" |
| OI-03 | **Muse API details**: endpoint, auth, model names, context window, pricing, JSON-schema support, tool/web-search support | `providers/muse.py`, `muse_search.py`, budgets | the router falls back to local |
| OI-04 | **Muse operating instructions** (workflow, approvals, reporting) | `MUSE_START_HERE.md` | the skeleton only |
| OI-05 | **Local model choice** + hardware (GPU/RAM) | `routing.yaml` local model name, `num_ctx`, chunk sizes | chunk size 3000 tokens |
| OI-06 | **Privacy**: may personal/confessional units be sent to the Muse API, or only to the local model? | routing of classify/psyche/shadow tasks | allowed (flag `privacy.personal_to_cloud: true`) |
| OI-07 | **Search provider**: SearXNG (self-hosted), Tavily (key), or Muse built-in | stage 4, stage 11 | SearXNG |
| OI-08 | **API keys** the author will obtain: CourtListener, Google Fact Check, TMDB | the corresponding fetchers | fetchers disabled |
| OI-09 | **Budget**: max cost per run, and per deep-research thread | `budget.py`, R-EXP-06 | 2M tokens/run; research always asks |
| OI-10 | 🟡 **PARTIAL**: the author-final Ch1 (`profile/manuscript/`) is the primary style exemplar; more samples are optional. Formerly: **Style samples**: 3–10 passages that best represent the author's voice | stage 8 voice | voice reports "no samples" |
| OI-11 | **Author profile** (via the interview or written directly) | context packs | minimal pack |
| OI-12 | **Gold set passages + labels** | `sots eval`, system audit | the audit reports "no gold set" |
| OI-13 | **Rubric weights and targets**: confirm or edit `rubrics.yaml` | Shadow grading | the defaults in `10 §2.1` |
| OI-14 | **Crisis resources** for the author's country (`safety.yaml`) | R-PSY-04 notice | a generic international list |
| OI-15 | **Style Guide approval**: review the generated Style Guide, protected terms (slang, coined words, names), intentional patterns | Pass A / Pass B | Pass A cannot start |
| OI-16 | **Persona set**: review/edit the template adult personas in the Persona Studio (cohort mix, backgrounds) | Audience Lab | the template set, marked "unreviewed" |
| OI-17 | **Reader Journey spec per chapter** (21 §3.1), set together from the chapter briefs | Audience targets | the global targets in 20 §5.2 |
| OI-18 | **Legal jurisdiction**: where the book will be published/sold; whether a publisher is involved | Legal Chamber (L7) | US primary + UK/CA/AU/EU secondary |
| OI-19 | **Pass A author review**: review Pass A hunks, or auto-apply them after the gates? | Act II | auto-apply after the gates |
| OI-20 | **Media exclusions**: works/creators the author never wants associated with the book | Media Scout | none |
| OI-21 | **LanguageTool setup**: Docker or Java on the author's machine; language variant (en-US/en-GB) | Mechanic | degraded LLM-only mode |
| OI-22 | **Grader threshold**: confirm 95 and max_attempts 4 (expect few items to pass at first) | the Quality Gate | 95 / 4 |
| OI-23 | **Beta readers**: will the author recruit real adult readers for calibration? | 20 §6 | synthetic-only, labeled |
| OI-24 | **Audience cohort weights**: confirm 60/30/10 (Gen Z adults / Millennials / Gen X) | Audience Lab | 60/30/10 |
| OI-26 | ✅ **RESOLVED 2026-09-28**: order approved `1·2·3·4·5·7·10·11·9·6·12·8`. Formerly: **Chapter order**: accept the PROPOSED order `1·2·3·4·5·7·10·11·9·6·12·8`, pick an alternative, or merge into 10 chapters (`profile/chapter_order_analysis.md`) | book_architecture, arc position, synthesis callbacks, brief edits | proposed order used, marked provisional |
| OI-27 | ✅ **RESOLVED 2026-09-28: NASB** is the main fact-checking and quote-gathering translation. Formerly: **Bible translation** for quotation checks (ESV / NIV / NKJV / other) | scripture checks (25 §5) | ESV |
| OI-28 | **Brief edits** listed in `book_architecture.yaml → brief_edits_required`: approve/reject each | Act 0 outputs, synthesis | flagged, not applied |
| OI-29 | **Protocol demand cap**: one "start here" protocol per chapter + an optional menu? A weekly time budget? | Protocol Load Auditor, Block 5 synthesis | all protocols kept; overload flagged |
| OI-30 | **Author profile confirmation**: `profile/author.md` was drafted from the briefs only | context packs, legal sensitivity | draft used |
| OI-31 | **Consent/anonymization** for the best friend (Ch5), family/teachers (Ch1), and the coffee-shop stranger (Ch3) | Legal L2 | anonymize by default |
| OI-32 | ✅ **RESOLVED 2026-09-28: KEEP** the named influencers; every factual statement is cross-checked; evaluations are framed as opinion (R-PROV-04); the Legal Chamber makes the kept version defensible. Formerly: **Named influencers in Ch4** (Sneako, RiceGum, Vlog Squad): keep with documented facts only, anonymize as archetypes, or cut | Legal L1/L2, R-PSY-02 | pre-opened HIGH legal issue |
| OI-33 | **Track `profile/` in git?** The foundation is currently gitignored as private (R-DATA-04) | backup/versioning | gitignored; FoundationChange records keep history |
| OI-34 | ✅ **RESOLVED 2026-09-29: NASB 2020.** The author's rule is "whatever is better for the audience to connect", and the 2020 revision's contemporary English suits adult Gen Z/Millennial readers. Exception: when another translation's familiar wording is itself the point, the system proposes either the NASB 2020 wording or an explicit translation label, and the author decides per quote (25 §5.1). Example: Ch1's "If the blind lead the blind, both shall fall into the ditch" appears to be KJV-style wording. | scripture checks | — |
| OI-35 | ✅ **RESOLVED 2026-09-29: foundational AND modifiable.** Ch1's structure is the foundation. Its **core transitions and concepts** are reused through the Signature Moves Library (29 §5), and each chapter may vary the form to fit its stories. | Block Synthesis layout | — |
| OI-36 | ✅ **RESOLVED 2026-09-29: APPROVED, and kept OPEN to additions** (the author: "keep it slightly open to be added to while we continue working"). **Provocation spiral promise** (Ch1 §4). Core plan: **plant** in ch03 B3 (Prosbolē), **full teardown** in ch04 B2+B4 (genealogy: scapegoat → Thucydides 3.82 Corcyra → yellow journalism → Brady 2021; Protocol 3 → the Spiral Audit), **exit** in ch12 B1. The core is fixed; the contents grow through the additions process in `profile/provocation_spiral_analysis.md §7`. OI-32 (named influencers kept) is unchanged. | Promise Ledger, ch03/ch04/ch12 synthesis | — |
| OI-37 | ✅ **RESOLVED 2026-09-29: Jordan Peterson's concept, heard live on tour in Tulsa, Oklahoma, in 2024** (the author attended). Provenance is a live source, attested by the author (25 §7). Ch1 §10 currently presents it as "I use a thought experiment" with no credit. That triggers an attribution Proposal for Ch1 (e.g. "Jordan Peterson described a version of this when I saw him in Tulsa in 2024…"). The fact-check verifies the tour stop; the ch03 anchor becomes a callback. | attribution | — |
| OI-38 | ✅ **RESOLVED 2026-09-29: context-dependent, not fixed.** Character types are chosen per story and lesson (author: "moved to the guidance of the stories told, and lessons learned"). Two constraints: (a) under the Promise Ledger, Ch1 names the perfectionist, big talker, rebel, and helper, so Ch2 must deliver those four and may add others; (b) any type attributed to Robert Greene must match Greene's actual list, and the author's own types are labelled as his. | ch02 synthesis | — |
| OI-39 | ✅ **RESOLVED 2026-09-29: prose-style evidence signals** (as in Ch1). Bracket tags stay off. | Formatter, Cross-Checker | — |
| OI-40 | **Raw→final pairs**: do you have the raw dictation or an earlier draft of Chapter 1? Adding it to `profile/voice_corpus/pairs/` trains the Transformation Model (29 §4), the single most valuable voice input. | Voice Lab, Block Synthesis | the transformation profile is inferred from the briefs + Ch1 only (low confidence) |
| OI-41 | **More voice material**: any writing you're willing to add to `profile/voice_corpus/` (final, drafts, spoken, casual, not-me examples). | Voice Model confidence → assessment strictness | Ch1 only (~16.5k words; corpus_confidence ≈ 0.45) |
| OI-25 | **Citation style**: Chicago notes (default) or another style | the Formatter, export | Chicago notes |

## B. Questions from Muse
_(append here: `- [date] [phase] question`)_

- [2026-10-02] [W0] **N-2 (APPLIED): arch-guard HTTP allowlist.** `research/fetchers/`
  + `research/search/` join `providers/` and `agents/tools/` as the only places
  that may touch the network (`tests/unit/test_architecture.py`). The 12 P07
  files (incl. `wikipedia.py`) now pass; anything else still fails.
- [2026-10-02] [W0] **N-3 (RECORDED): Lane A owns `voice/` end to end.**
  Only the integrator touches `voice/` in W0 (nothing needed touching);
  from W1 on, all voice work (P11A + voice tasks) is Lane A's.
- [2026-10-02] [W0] **N-4 (RECORDED): Lane B verifies the partial P07 code.**
  P07 is ~40% present, 0/24 boxes, with ruff/pyright errors. W0 applies only
  the N-2 allowlist; Lane B verifies task by task and completes it in W1.
- [2026-10-02] [W0] **AQ-W0-1 (ANSWERED): Muse starts from the beginning.**
  The W0 integrator session re-read the full blueprint order, re-verified
  P00–P06 + P04A + vault task by task (evidence in `sots-coord/evidence/I/W0.md`),
  then executed the Wave 0 plan. No box needed un-ticking.
- [2026-10-02] [W0] **AD-1…AD-7 (RECORDED, full text in `coord/DECISIONS.md`
  D-001…D-007).** AD-1: parallel lanes approved as an explicit R-SCOPE-03
  exception (strict order inside each lane; cross-lane deps gate on merges).
  AD-2: deferred-by-plan tasks allowed. AD-3: baseline commit approved.
  AD-4: W0 hotspot splits approved (`storage/repo/` package; R-CODE-03
  overrides the 02 §5 wording). AD-5: the 400-line limit covers
  `src/**/*.py` only. AD-6: coordination folder path approved. AD-7:
  profile junction approved.
- [2026-10-02] [W0] **New files outside the 02 §4 folder tree (RECORDED).**
  `commands/`, `invariant_plugins.py`, the 7 `agents/` helper modules,
  `storage/repo/`, `vault/readme.py`, `ingest/invariants.py`,
  `segment/invariants.py`, and the TUI screen registry were created in W0
  and are not in the 02 §4 tree; the integrator owns them until the
  lanes' phases land (D-004/D-013, OWNERSHIP_MAP W0 notes).
- [2026-10-02] [W0] **CORRECTION: coordination lives at in-repo `coord/`.**
  The `sots-coord/evidence/I/W0.md` path in the AQ-W0-1 note above is
  superseded: serial mode (D-013, AD-6's blessed alt path) puts the live
  folder at `coord/`, so the evidence is at `coord/evidence/I/W0.md`.

## C. Ideas (not approved)
_(append here; nothing in this list gets built without author approval)_

## D. Author-approved additions (appended; built on the author's direct request)
- **OI-42 — Obsidian vault mirror (APPROVED 2026-09-29, author request).**
  SotS maintains an Obsidian vault (`data/vault/` by default, `paths.vault_dir`)
  mirroring the Book Foundation: `Book Index.md`, `Chapters/`, `Anchors/`,
  `Messages/`, `Motifs/`, `Architecture/`, with `[[wikilinks]]` for
  cross-chapter reuse, motif serials, and reading order. SQLite stays the system
  of record for runs; the vault keeps chapter context and whole-book threads
  navigable. Sync is idempotent, preserves `## Author notes` sections, and never
  deletes. Commands: `sots vault init|sync|status`. Settings: `vault.*`.
  Chapter short titles in `vault/paths.py` are provisional like the draft
  foundation; filenames stay stable so links never break.
- **OI-42b — Vault phase 2 (same approval, 2026-09-29).** Whole-book context:
  `Book Dashboard.md` (per-chapter counts, 37-protocol inventory, reuse
  hotspots, message coverage), a `## Pipeline state` section in each chapter
  note read from SQLite `chapter_state` (graceful "not run" text when the DB
  is absent), and `sots vault digest` collecting `## Author notes` margin
  sections into `Author Notes Digest.md`. Only managed notes are digested;
  scaffolding and freeform notes are left alone.
