# 02 — ARCHITECTURE

## 1. What SotS does (plain language)

The author pastes or loads raw writing (a "word vomit") for the self-help / reflective book.
SotS then:

1. **Breaks it into atomic units.** Each unit is one statement, story beat, or idea.
2. **Labels each unit.** Is it a personal experience, a belief, a narrative device, a lesson,
   a factual claim (statistic, court case, social media case…), or a media reference
   (book, film, TV, music…)?
3. **Researches and fact-checks** every checkable unit against real-world sources, and grades
   *how* true it is and *what kind* of truth it rests on (primary record, academic,
   journalism, social media story, fiction).
4. **Checks the author's retelling of media**: the plot facts, the quotes, the attribution,
   and whether the author's reading of the work's message holds up.
5. **Runs the psyche engines**: interacting lenses for emotion, thinking patterns, themes,
   archetypes and arc, blind spots, and reader impact.
6. **Tracks the book's core messages**: which messages this text serves, where it drifts,
   how it flows, and whether it sounds like the author.
7. **Runs the Shadow Self**: the strongest honest critic. It asks the questions the author
   may be avoiding and grades the text against measurable rubrics.
8. **Shows everything in a terminal UI** and writes Markdown and JSON reports.
9. **Builds outward (Expansion Team, stage 11):** maps concepts across all the word vomits,
   proposes directions to deepen, runs approval-gated deep research, writes cited reports,
   converses with the text (margin notes + chat), and proposes how to integrate findings.
   See `11_EXPANSION_TEAM.md`.

10. **Rewrites in two gated passes**: Pass A (mid-process polish) and Pass B (the final
    master rewrite). Each pass has a Style Analyst and a Reference Cross-Checker that must
    both approve (`19`).
11. **Tests the text on simulated adult readers** (Gen Z adults, Millennials, a Gen X
    outside view) plus text-mechanics analysts, and loops the numbers back into the
    rewriter (`20`, `21`).
12. **Runs an eight-counsel Legal Chamber** that must reach a cohesive defense of the
    text's positions before the book moves on (`22`).
13. **Pitches projects to the author**: the fact-check and expansion teams bring graded
    (≥ 95) proposals with questions and placement options (`17`, `18`).

All agents run on one shared runtime with failsafes (`16`). Free-form drafting of new
chapters from nothing (the `writer/` stub) stays locked (R-SCOPE-02).

## 2A. The six Acts (the master flow)

The stages below (§2) are **Act I**. The whole system runs as six Acts per chapter:

```
ACT 0   BRIEF AUDIT once per brief version: verify every anchor in profile/anchors.yaml,
                    protocol evidence grades, internal consistency, audience/legal pre-flags  (doc 23 §4)
          │
ACT I   ANALYZE     stages 1–10: ingest → segment → classify → research/verify → media → psyche
                    → narrative/voice → shadow → report                         (docs 05–10)
          │
ACT II-D DRAFT     Block Synthesis: dictation units → BlockPlan → block draft (per block 1→6)
                    → preservation ∥ style ∥ cross-check → gate block_draft ≥ 95 → stitch  (doc 24)
          │
ACT II  MID POLISH  Rewrite Pass A: Mechanic → Formatter → Line Editor
                    → Style Analyst ∥ Reference Cross-Checker → GATE A            (doc 19 §3)
          │ (Gate A passed)
ACT III AUDIENCE    Mechanics Panel ∥ Persona Panel → Scorecard → Audience Brief (G-AUD)
                    → Line Editor audience edits → Gate A again → re-test (≤ 3 loops) (doc 20)
          │
ACT IV  LEGAL       Intake → 8 counsel: blind review → positions → cross-exam → scoring
                    → Defense Memo (G-LEGAL) → endorsement ≥ 6/8 → legal edits
                    → cross-check  (BLOCKS the chapter until resolved)            (doc 22)
          │
ACT V   DISCOVER    (may start any time after Act I, in the background)
                    Discovery Scout + Media Scout + Expansion Team → proposals
                    → Quality Gate (≥ 95) → Proposal Desk → author decisions
                    → IntegrationPlan                                             (docs 06 §9, 11, 17, 18)
          │ (Acts IV done, and the author has finished deciding on proposals for this chapter)
ACT VI  MASTER      Rewrite Pass B: Weaver → Master Rewriter → Mechanic → Formatter
                    → Style ∥ Cross-Check → GATE B → Legal Delta Review → Audience no-regression
                    → Shadow final grade → hunks graded (G-HUNK-B) → author hunk review
                    → EXPORT the master manuscript                                (docs 19 §4, 22 §7, 20 §5.3, 10)
          │
ON REQUEST  RECHECK & REASON   Intent Keepers + Counter-Council → one graded Reasoning Report  (doc 26)
MILESTONE   MASTER AUDIT      frozen verified test battery (CCAT) over the whole book → MASTER version  (doc 28)
ALWAYS      MASTER GRADING ENGINE  the single judge every agent relies on: Factual + Emotional + Professional Panel  (doc 27)
AFTER   LEARN       playbook, calibration, grader health, prompt trials → author-approved changes (doc 20 §7)
```

Act rules:
- Acts run **per chapter**. Different chapters may be in different Acts. Act 0 runs per brief
  version (all chapters).
- Every act loads the **Book Foundation** (doc 23): book, author, messages, style seed, anchors,
  architecture, and chapter briefs. The foundation is the starting point agents build from, and
  they may propose to expand it (R-FOUND-02).
- `sots run` = Act I. `sots act <II|III|IV|V|VI> <chapter_id>` runs a later act. `sots advance
  <chapter_id>` runs the next eligible act.
- The orchestrator stores `chapter_state` (`act`, `gate_status`, `blocked_reasons`) and refuses
  to start an act whose prerequisites or gates are not met (R-GATE-03).
- After every act: the F20 invariants run (16 §5).

## 2. Pipeline

```
 raw text ──► [1 INGEST] ──► [2 SEGMENT] ──► [3 CLASSIFY] ──┬──► [4 RESEARCH] ──► [5 VERIFY] ──┐
                                                            ├──► [6 MEDIA CHECK] ─────────────┤
                                                            │                                 ▼
                                                            └──────────────► [7 PSYCHE ENGINES]
                                                                                      │
 profile/ (author, book, chapter briefs, messages, style samples) ─ feeds every stage │
                                                                                      ▼
                                              [8 NARRATIVE & VOICE] ──► [9 SHADOW SELF]
                                                                                      │
                                                                                      ▼
                                                                      [10 REPORT] ──► TUI / files
```

Stage dependencies (the orchestrator must enforce them):

| Stage | Needs finished | Runs on |
|-------|----------------|---------|
| 1 ingest | — | document |
| 2 segment | 1 | chunks |
| 3 classify | 2 | units |
| 4 research | 3 | units where `checkability != NOT_CHECKABLE` and `content_type == FACTUAL_CLAIM` |
| 5 verify | 4 | same units as 4 |
| 6 media | 3 | units where `content_type == MEDIA_REFERENCE` |
| 7 psyche | 3, 5, 6 | all units + chunk summaries |
| 8 narrative | 3, 7 | all units + profile |
| 9 shadow | 5, 6, 7, 8 | everything |
| 10 report | 9 | run |
| 11 expansion | 9 (map/propose); author approval (research) | all documents + concept graph |

Stage 11 is **not** part of `sots run`. It runs through `sots expand …` commands or the TUI,
because deep research is costly and approval-gated (R-EXP-06).

Stages 4–5 and stage 6 may run concurrently. Everything else runs in order.

## 3. Core concepts

- **Document**: one ingested input file or paste. Immutable.
- **Chunk**: a token-bounded slice of a document, used only for processing.
- **Unit**: one atomic statement or idea, with character offsets into the document.
  **The unit is the main object of the whole system.**
- **Run**: one execution of the pipeline over one or more documents. Every result belongs to
  a run.
- **Profile**: the author's standing context: who they are, the book premise, the chapter
  briefs, the core messages, and style samples. Loaded into every relevant LLM call.
- **Board**: the shared blackboard the psyche engines read from and write to.

## 4. Folder tree (build exactly this)

```
SotS/
├── MUSE_START_HERE.md
├── BUILD_LOG.md                      # created by Muse, appended each phase
├── blueprint/                        # these documents (read-only for Muse)
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   ├── settings.yaml                 # paths, budgets, chunk sizes, feature flags
│   ├── routing.yaml                  # which provider/model handles which task
│   ├── source_tiers.yaml             # domain → tier and source_class
│   ├── rubrics.yaml                  # Shadow Self rubrics and targets
│   ├── system_goals.yaml             # measurable targets for the code itself
│   ├── safety.yaml                   # crisis-resource text + banned clinical labels
│   ├── teams.yaml                    # team registry (16 §6)
│   ├── agents/<team>/<agent>.yaml    # Agent Cards (16 §1)
│   ├── grader.yaml                   # gates + rubrics (17)
│   ├── formatting.yaml               # manuscript + citation style (19 §1.3)
│   ├── personas.yaml                 # adult reader personas (20 §4.1)
│   ├── audience/                     # thresholds.yaml targets.yaml techniques.yaml cliches.txt
│   │                                 # dated_slang.txt therapy_speak.txt caricature_markers.txt
│   └── legal.yaml                    # jurisdictions, counsel roster, exit thresholds (22)
├── profile/                          # AUTHOR'S PRIVATE CONTEXT (gitignored)
│   ├── author.md                     # who the author is (from guided interview)
│   ├── book.md                       # premise, audience, promise to the reader
│   ├── messages.yaml                 # core messages (book level + per chapter), DRAFT v0
│   ├── style_guide_seed.yaml         # voice rules + protected terms from the briefs (23)
│   ├── anchors.yaml                  # Anchor Registry: every anchor in the 12 briefs (23)
│   ├── book_architecture.yaml        # reading order (APPROVED 2026-09-28), phases, arc, motif serials
│   ├── intent_model.yaml             # Author Intent Model (26 §2), built by the Intent Cartographer; the author confirms
│   ├── CORE_MESSAGES_REVIEW.md       # a readable review sheet for messages.yaml
│   ├── chapter_order_analysis.md     # the 5-analyst ordering study
│   ├── voice_corpus/                 # Voice Lab intake (29): final/ drafts/ spoken/ casual/ pairs/ not_me/, manifest.yaml, signature_moves.yaml
│   ├── manuscript/                   # AUTHOR-FINAL chapters (immutable) + per-chapter analysis
│   │   ├── ch01_the_modern_day.md    # the reference chapter (voice, form, honesty)
│   │   └── ch01_analysis.md
│   ├── chapters/
│   │   ├── ch01_brief.md … ch12_brief.md   # full brief text (lossless)
│   │   ├── ch01.yaml … ch12.yaml     # structured briefs (generated by the Brief Parser, then reviewed)
│   │   └── source/*.docx             # original briefs
│   └── (style_samples/ retired: the author's writing now goes in voice_corpus/, see 29)
├── supplements/                      # author-supplied reference material (PDFs, notes, links)
├── prompts/
│   ├── segment/extract_units.v1.md
│   ├── classify/classify_unit.v1.md
│   ├── research/plan_queries.v1.md
│   ├── verify/researcher.v1.md
│   ├── verify/skeptic.v1.md
│   ├── verify/adjudicator.v1.md
│   ├── media/media_check.v1.md
│   ├── psyche/<engine>.v1.md         # one per engine
│   ├── narrative/map_messages.v1.md
│   ├── narrative/voice_compare.v1.md
│   ├── expand/*.v1.md                # see 11_EXPANSION_TEAM.md §7
│   ├── fact_check/*.v1.md            # specialists + scouts (06 §9)
│   ├── grader/*.v1.md                # judge_strict, judge_reader, judge_tiebreak, feedback
│   ├── proposals/*.v1.md
│   ├── rewrite/*.v1.md
│   ├── audience/*.v1.md              # one persona_read prompt + the analysts + the brief
│   ├── legal/*.v1.md                 # L1…L8 + screen + synthesize
│   ├── learning/*.v1.md
│   ├── shadow/shadow_reflect.v1.md
│   ├── shadow/rubric_grade.v1.md
│   └── summarize/summarize_chunk.v1.md
├── src/sots/
│   ├── __init__.py
│   ├── cli.py                        # Typer entry point: `sots …`
│   ├── config.py                     # loads YAML + .env → frozen Settings
│   ├── errors.py                     # all custom exceptions
│   ├── models/                       # Pydantic models (see 03_DATA_MODELS.md)
│   │   ├── enums.py
│   │   ├── document.py
│   │   ├── unit.py
│   │   ├── evidence.py
│   │   ├── verdict.py
│   │   ├── media.py
│   │   ├── psyche.py
│   │   ├── narrative.py
│   │   ├── shadow.py
│   │   ├── profile.py
│   │   ├── expansion.py              # see 11_EXPANSION_TEAM.md §3
│   │   └── run.py
│   ├── storage/
│   │   ├── schema.sql
│   │   ├── db.py                     # connection, migrations
│   │   └── repo.py                   # typed read/write functions per model
│   ├── providers/
│   │   ├── base.py                   # LLMProvider protocol
│   │   ├── fake.py                   # deterministic test provider
│   │   ├── local_ollama.py
│   │   ├── muse.py
│   │   ├── router.py                 # task → provider/model from routing.yaml
│   │   ├── structured.py             # call → validate → retry (R-LLM-03)
│   │   ├── cache.py
│   │   ├── budget.py                 # token counting, cost tracking, limits
│   │   └── context_pack.py           # builds the context for each call
│   ├── profile/
│   │   ├── loader.py
│   │   └── interview.py              # guided first-run interview
│   ├── ingest/
│   │   ├── loader.py                 # .txt .md .docx .pdf → text
│   │   └── normalize.py
│   ├── segment/
│   │   ├── chunker.py
│   │   ├── extractor.py
│   │   └── summarizer.py             # the summary tree
│   ├── classify/
│   │   ├── classifier.py
│   │   └── safety_scan.py            # R-PSY-04
│   ├── research/
│   │   ├── planner.py                # queries per unit
│   │   ├── search/                   # base.py, muse_search.py, searxng.py, tavily.py
│   │   ├── fetchers/                 # web.py, wikipedia.py, courtlistener.py, openalex.py,
│   │   │                             # crossref.py, google_factcheck.py, tmdb.py,
│   │   │                             # openlibrary.py, musicbrainz.py, supplements.py
│   │   ├── tiers.py                  # applies source_tiers.yaml
│   │   └── evidence_builder.py
│   ├── verify/
│   │   ├── citation_check.py         # R-TRUTH-02
│   │   ├── researcher.py
│   │   ├── skeptic.py
│   │   ├── adjudicator.py
│   │   └── rules.py                  # deterministic verdict caps (R-TRUTH-03)
│   ├── media/
│   │   ├── identify.py               # resolve the work (title/creator/year)
│   │   └── checker.py
│   ├── psyche/
│   │   ├── board.py
│   │   ├── registry.py               # engine list + dependency order
│   │   ├── triggers.py               # cross-engine trigger rules
│   │   ├── engines/                  # emotion.py cognitive.py theme.py archetype.py
│   │   │                             # blindspot.py reader.py
│   │   └── synthesizer.py
│   ├── narrative/
│   │   ├── ledger.py                 # unit → message mapping
│   │   ├── drift.py
│   │   ├── flow.py
│   │   └── voice.py                  # style fingerprint + comparison
│   ├── shadow/
│   │   ├── reflect.py
│   │   ├── rubric.py
│   │   ├── goals.py                  # writing goals + trend across runs
│   │   └── system_audit.py           # grades the system itself
│   ├── pipeline/
│   │   ├── stages.py
│   │   └── orchestrator.py
│   ├── reports/
│   │   ├── markdown.py
│   │   └── export.py
│   ├── tui/
│   │   ├── app.py
│   │   ├── widgets/
│   │   └── screens/
│   ├── expand/                       # Expansion Team (see 11_EXPANSION_TEAM.md §7)
│   ├── agents/                       # shared runtime (16): base.py cards.py events.py
│   │   ├── tools/                    # one module per tool (16 §3)
│   │   └── failsafes/                # F01–F20 (16 §5)
│   ├── grader/                       # quality gate (17): hard_checks.py measured.py judges.py loop.py calibration.py
│   ├── proposals/                    # proposal desk (18): builder.py question_check.py queue.py desk.py plan.py
│   ├── rewrite/                      # Pass A/B (19): mechanic.py formatter.py line_editor.py master.py weaver.py
│   │                                 # style_guide.py style_analyst.py cross_checker.py meaning.py anchor.py gates.py
│   ├── audience/                     # audience lab (20): metrics/ panel.py personas.py aggregate.py brief.py calibration.py
│   ├── legal/                        # legal chamber (22): intake.py clerk.py counsel.py synthesizer.py delta.py
│   ├── learning/                     # playbook.py prompt_trials.py inbox.py (20 §7)
│   ├── foundation/                   # loader.py cards.py anchors.py architecture.py versioning.py (23)
│   ├── brief_audit/                  # Act 0 (23 §4)
│   ├── voice/                        # Voice Lab (29): corpus.py features/ model.py similarity.py scaling.py transform.py moves.py explain.py
│   ├── mge/                          # Master Grading Engine (27): sections.py panel.py profiles.py stability.py
│   ├── reason/                       # Recheck & Reason (26): aim.py keepers/ council/ protocol.py report.py
│   ├── audit/                        # Master Audit (28): testgen.py battery.py runner.py certify.py
│   ├── synthesis/                    # Block Synthesis (24): assembler.py architect.py synthesizer.py preservation.py stitch.py
│   ├── discovery/                    # discovery + media scouts (06 §9.3)
│   ├── acts/                         # act orchestration: act1.py … act6.py chapter_state.py
│   └── writer/
│       └── __init__.py               # stub: raises WriterDisabledError
├── data/                             # gitignored, created at runtime
│   ├── sots.db
│   ├── inbox/                        # immutable raw copies
│   ├── cache/                        # LLM + fetch cache
│   ├── runs/<run_id>/                # reports per run (+ revisions/, legal/, expand/)
│   ├── exports/<book>/<date>/        # master manuscript output (19 §6)
│   └── logs/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── eval/
    ├── gold/                         # hand-labeled passages (see 14_TESTING_AND_EVAL.md)
    └── run_eval.py
```

## 5. Storage

- SQLite at `data/sots.db`, using the stdlib `sqlite3` module (no ORM).
- `storage/schema.sql` creates one table per model in `03_DATA_MODELS.md`. List and dict
  fields are stored as JSON text columns.
- `storage/repo.py` is the **only** module that runs SQL.
- Turn on WAL mode. Use foreign keys. Keep a `schema_version` table for migrations.

## 6. Allowed dependencies

| Package | Purpose |
|---------|---------|
| pydantic ≥2 | all data models |
| typer | CLI |
| textual, rich | TUI and pretty output |
| httpx | every HTTP call (async) |
| pyyaml | config |
| python-dotenv | .env |
| trafilatura | extracting readable text from web pages |
| rapidfuzz | excerpt verification, dedup |
| python-docx, pypdf | ingesting .docx / .pdf |
| tenacity | retry/backoff on HTTP calls |
| pytest, pytest-asyncio, respx | tests |
| ruff, pyright | lint, type checking |

Package manager: `uv`. Install command: `uv sync`. Run command: `uv run sots …`.

## 7. Concurrency

- All network I/O is `async` (httpx.AsyncClient).
- A semaphore limits concurrent calls per provider (`settings.yaml: concurrency.<provider>`).
- The orchestrator runs units in batches. The batch size comes from settings.
