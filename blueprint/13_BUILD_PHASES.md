# 13 — BUILD PHASES

Build in this order. **A phase is done only when every acceptance check passes.** The
granular, numbered steps for each phase are in `tasks/` (one file per phase). Each check here
is also a task in that file.

Every phase also requires: `ruff check` clean, `pyright` clean, `pytest` green (live tests
skipped), `sots doctor` green (from P03 on), no release-blocker regression in `sots eval`
(from P13 on), and one line in `BUILD_LOG.md`.

| Phase | Name | Act | Tasks file |
|---|---|---|---|
| P00 | Skeleton | — | `tasks/P00_skeleton.md` |
| P01 | Models + storage | — | `tasks/P01_models_storage.md` |
| P02 | Providers | — | `tasks/P02_providers.md` |
| P03 | Agent runtime, tools, failsafes | — | `tasks/P03_agent_runtime.md` |
| P04 | Profile + ingest | I | `tasks/P04_profile_ingest.md` |
| P04A | **Book Foundation layer** (loader, cards, anchors, architecture, brief parser, dictation keying) | all | `tasks/P04A_foundation.md` |
| P05 | Segment + summarize | I | `tasks/P05_segment.md` |
| P06 | Classify + safety scan | I | `tasks/P06_classify.md` |
| P07 | Research tools | I | `tasks/P07_research_tools.md` |
| P08 | Fact-check team | I | `tasks/P08_fact_check_team.md` |
| P09 | Media accuracy | I | `tasks/P09_media.md` |
| P10 | Psyche engines | I | `tasks/P10_psyche.md` |
| P11 | Narrative + voice | I | `tasks/P11_narrative_voice.md` |
| P11A | **Voice Lab** (corpus intake, 120+ features, confidence-weighted model, scaled assessments, Transformation Model, Signature Moves) | all | `tasks/P11A_voice_lab.md` |
| P12 | Shadow + rubrics + system audit | I | `tasks/P12_shadow.md` |
| P13 | Act I orchestration + reports + core CLI | I | `tasks/P13_act1_orchestration.md` |
| P13A | **Act 0 Brief Audit** (anchor verification, evidence grades, epistemic tiers, scripture checks) | 0 | `tasks/P13A_brief_audit.md` |
| P14 | Quality Gate Grader | all | `tasks/P14_grader.md` |
| P14M | **Master Grading Engine** (Factual + Emotional sections, Professional Panel, stability, one-master-answer) | all | `tasks/P14M_master_grading_engine.md` |
| P14A | **Block Synthesis** (Act II-D drafting) | II-D | `tasks/P14A_block_synthesis.md` |
| P15 | Rewrite Pass A (Mid Polish) | II | `tasks/P15_rewrite_pass_a.md` |
| P16 | Audience Lab | III | `tasks/P16_audience_lab.md` |
| P17 | Legal Chamber | IV | `tasks/P17_legal_chamber.md` |
| P18 | Discovery scouts + Expansion Team | V | `tasks/P18_discovery_expansion.md` |
| P19 | Proposal Desk | V | `tasks/P19_proposal_desk.md` |
| P20 | Rewrite Pass B + Legal Delta + Export | VI | `tasks/P20_master_rewrite.md` |
| P21 | Learning loop | after VI | `tasks/P21_learning.md` |
| P21A | **Recheck & Reason** (Intent Keepers + Counter-Council, on request only) | on request | `tasks/P21A_reason_and_counter_council.md` |
| P22 | TUI | — | `tasks/P22_tui.md` |
| P23 | Evaluation + live shakedown | — | `tasks/P23_eval_live.md` |
| P24 | **Master Audit** (the final build section; a low-frequency milestone tool) | milestone | `tasks/P24_master_audit.md` |
| P25 | Writer (free drafting) | — | **LOCKED**: do not start |

**Why this order:** the shared runtime (P03) comes before any agent. The Grader (P14) comes
before every team whose output reaches the author. Legal (P17) is built after Pass A and the
Audience Lab, because it runs on their validated output. The TUI (P22) is built last over a
stable core, and the CLI covers everything until then.

---

## Acceptance checks by phase

### P00 — Skeleton
- [ ] `uv sync` succeeds; `uv run sots --help` lists every command in `12 §1` and `12 §3.1` (stubs allowed).
- [ ] `uv run sots write` exits with code 2.
- [ ] `Settings` loads from the sample config; a missing required key raises `ConfigError`.
- [ ] `sots init` creates `data/sots.db` and the templates, and is idempotent.

### P01 — Models + storage
- [ ] A round-trip test for every model in 03, 11 §3, 16, 17, 18, 19, 20, 22.
- [ ] `extra="forbid"` is enforced; `schema_version` migrations work from an empty DB.

### P02 — Providers
- [ ] Invalid JSON → 2 retries → FAILED; cache hit on an identical call; budget exceeded raises; router fallback is recorded; context packs never exceed budget or end mid-sentence.

### P03 — Agent runtime, tools, failsafes
- [ ] Every failsafe F01–F20 has at least one dedicated test that triggers it.
- [ ] Agent Card validation: bad cards fail `sots doctor`.
- [ ] A demo agent (a fake provider scripted with tool actions) completes a 3-step tool loop, checkpoints, is killed, and resumes at step 3.
- [ ] Loop detection (F04) and injection stripping (F13) are proven by fixtures.
- [ ] `compute` rejects any non-whitelisted expression.

### P04 — Profile + ingest
- [ ] The same content in .txt/.md/.docx/.pdf → the same normalized text; inbox byte-identical; sha256 recorded; duplicate detected; `profile check` lists missing files.

### P05 — Segment + summarize
- [ ] Offset integrity on 3 fixtures (one > 50k words); coverage ≥ 85%; overlap dedup; a single-root summary tree.

### P06 — Classify + safety scan
- [ ] Every consistency rule is tested; embedded claims become children; the review queue works; the safety flag doesn't block.

### P07 — Research tools
- [ ] Every fetcher is tested with respx; `verify_excerpt` behaves on exact/fuzzy/invented; missing keys disable cleanly; the planner adds the counter-evidence query + required lookups; tier mapping is correct.

### P08 — Fact-check team
- [ ] Each VR-* rule has a unit test; min(proposed, caps) is tested; fiction → CONTEXT; the confidence formula matches hand-computed values; HIGH objections must be addressed.
- [ ] Each specialist is routed by claim_kind; the statistics specialist recomputes a figure from a parsed fixture table.
- [ ] DiscoveryNotes are capped at 3 per unit and must carry verified evidence.

### P09 — Media accuracy
- [ ] Correct resolution / unresolved below 85; attribution points from a wrong year or creator; downgrade rules; no excerpt > 300 chars; no lyrics stored.

### P10 — Psyche engines
- [ ] Layer order enforced; unit-id and question requirements; TR-01…TR-07 tests; synthesizer id validation; banned clinical labels are absent.

### P11 — Narrative + voice
- [ ] Drift metrics and fingerprint metrics match hand-computed values; graceful behaviour without messages.yaml.

### P11A — Voice Lab
- [ ] Every intake path (folder sync, CLI add, TUI) registers samples with a register, weight, and hash. Ch1 is auto-registered as final ×2.0.
- [ ] ≥ 120 features are implemented across the 10 families, each with a unit test on a hand-computed passage.
- [ ] The importance, confidence, shrinkage, and recency formulas (29 §3) match hand calculations on a 3-sample fixture.
- [ ] Scaled thresholds: with Ch1 only, the effective thresholds sit below base. Adding 40k fixture words raises them toward base (monotonic test).
- [ ] VOICE(t): held-out Ch1 paragraphs score high; the not_me/AI-cliché fixture scores low; the explanations name the right features.
- [ ] The Transformation Model learns deltas from a pairs fixture. The Style Guide is generated from the model.

### P12 — Shadow + rubrics + audit
- [ ] Measured criteria come from bands only; the YAML drives scores; trend vs the previous run; hard goals block; `sots audit` covers every goal.

### P13 — Act I orchestration + reports
- [ ] A full Act I on a fixture with FakeProvider; kill + resume without redoing work; `--dry-run` makes 0 calls; the report order is correct; `chapter_state` is set to "I done".

### P04A — Book Foundation
- [ ] Every foundation file loads and validates; chapter ids ch01–ch12 resolve; every anchor id referenced by a structured brief exists in anchors.yaml.
- [ ] Context pieces F1–F6 are built within budget for any chapter/block.
- [ ] Dictation keyed with `### ch03.B2.P1` markers maps units to block/prompt; unmarked text is block-mapped.
- [ ] The dictation-coverage report lists answered and missing prompts.
- [ ] A foundation change bumps the version and records a FoundationChange; runs record the versions used.

### P13A — Act 0 Brief Audit
- [ ] Every anchor in anchors.yaml receives a VerdictRecord (or a documented NOT_CHECKABLE / media / scripture result).
- [ ] The epistemic tier is computed (ET-01), and author-tag mismatches are flagged (ET-02).
- [ ] Protocol evidence grades are audited (EG-01…04); scripture quotes/terms are checked (SC rules).
- [ ] Every non-NASB-2020 quote raises a per-quote translation Proposal (25 §5.1); the Ch1 Matthew 15:14 fixture is detected as KJV wording.
- [ ] Live-source anchors are event-verified, and uncredited uses in author-final chapters raise attribution Proposals (the Ch1 §10 bookshelf fixture).
- [ ] Internal consistency checks catch the known fixtures: ch06.A02 (numbers), ch12.A07 (chronology), the phase-label conflicts.
- [ ] Findings reach the author only as graded proposals (≥ 95).

### P14 — Quality Gate Grader
- [ ] Hard-check failure → score 0; measured criteria are never taken from the LLM; min-of-two judges; the tiebreak fires on a ≥ 2-point gap.
- [ ] The regeneration loop stops at pass / max_attempts / plateau (3 tests).
- [ ] GR-01…GR-05 each have a test (e.g. the producer's prompt never contains the rubric anchors).
- [ ] Health signals compute on a synthetic history.

### P14A — Block Synthesis
- [ ] The BlockPlan accounts for every block unit (used or dropped with a reason).
- [ ] R-SYN-01: an invented-memory fixture fails the preservation audit.
- [ ] R-SYN-02: must-keep units survive verbatim (fuzzy ≥ 95).
- [ ] R-SYN-03: a FALSE unit is written only in its verified-correction form, and flagged.
- [ ] R-SYN-04: an unanswered prompt → an `[[AUTHOR: …]]` placeholder; export refuses while one remains.
- [ ] R-SYN-07: the author-proportion floor is measured and enforced.
- [ ] `block_draft` ≥ 95 gate + regeneration loop; the stitch pass writes only seam sentences.

### P15 — Rewrite Pass A
- [ ] LanguageTool client works against a mocked server; the protected-terms ignore list is sent.
- [ ] The Mechanic's adjudicator keeps an intentional fragment listed in the Style Guide.
- [ ] The Formatter is idempotent (formatting twice = once).
- [ ] The edit budget is enforced per paragraph.
- [ ] Meaning check: a negation flip is caught; a number change without authorization is caught.
- [ ] Cross-checker: `drifted`, `new_unverified_claim`, and `lost_attribution` fixtures each fail the gate.
- [ ] Gate A: the loop runs ≤ 3 times, then escalates.
- [ ] Unit re-anchoring keeps every original unit traceable.

### P16 — Audience Lab
- [ ] Persona loader rejects age < 18 and warns on diversity gaps.
- [ ] Caricature markers → the reaction is rejected; generic reactions without a quote are rejected.
- [ ] Every mechanics metric matches hand-computed values on a fixture.
- [ ] The aggregator's MRR, hotspots, and strong lines are correct on a synthetic reaction set.
- [ ] The loop rejects edits below the voice floor, and reverts on regression.
- [ ] Panel collapse (low SD) is flagged.
- [ ] CSV import + calibration bias computed; under-18 rows rejected.

### P17 — Legal Chamber
- [ ] Intake flags each issue type on fixtures.
- [ ] The Clerk runs R0–R6; exit requires ≥ 6/8 + no HIGH + memo ≥ 95.
- [ ] A top-2-scored dissent that isn't answered → the memo fails.
- [ ] Deferring positions without their own reasoning are rejected.
- [ ] A fabricated authority (the URL doesn't contain the excerpt) is rejected, and the counter increments.
- [ ] After 3 cycles without exit → BLOCKED; Act VI refuses to start for that chapter.
- [ ] The banner appears in every legal output.

### P18 — Discovery + Expansion
- [ ] Concept merge: fixture duplicates merge; distinct concepts do not. Graph metrics (hubs/bridges/orphans) match a hand-built graph.
- [ ] Each Explorer recipe (11 §4.2) fires on its fixture trigger; research never starts without approval (R-EXP-06).
- [ ] The deep-research loop stops on each of its 4 stop conditions.
- [ ] The report validator removes uncited factual statements; counter_perspectives is never empty; reports pass G-REPORT ≥ 95.
- [ ] Prompt-injection fixture: a fetched page with embedded instructions doesn't change behaviour (R-EXP-04).
- [ ] Every stored text has an `origin`; the Integrator output has no paragraph > 60 words (R-EXP-08).
- [ ] The Media Scout filters out works that are unresolved, already cited, or excluded.
- [ ] Expansion outputs become Proposals (never raw) with ≥ 2 placements/modes.

### P19 — Proposal Desk
- [ ] The question validator rejects generic/leading questions and accepts the 18 §3 patterns.
- [ ] The queue caps at max_open; priority ordering; dedup merges.
- [ ] Nothing below 95 is ever presented (R-GATE-01).
- [ ] A modify → regenerate → re-grade path works.
- [ ] An accepted proposal creates an IntegrationPlanItem.

### P20 — Pass B + Legal Delta + Export
- [ ] The Weaver uses only author answers + evidence (a fixture with an invented memory is caught by the cross-checker as `new_unverified_claim` or by the personal-content check).
- [ ] Gate B's stricter thresholds; 0 `[[VERIFY]]` markers; endnotes resolve.
- [ ] The Legal Delta scope contains only the changed/woven hunks; resolved memos re-validate.
- [ ] Audience no-regression enforced.
- [ ] Author hunk review applies the decisions; the export produces every file in 19 §6.

### P21 — Learning loop
- [ ] Playbook posteriors update from fixture outcomes; LR-02 filtering.
- [ ] Prompt trials: promote only on improvement with no regression (replay-based test).
- [ ] Every change goes through the inbox; rollback restores the previous version.

### P22 — TUI
- [ ] Every screen in 12 §2.2 and 12 §3.2 opens under Pilot with a seeded DB.
- [ ] The UI stays responsive during long workers.
- [ ] Origin colors, verdict labels, the simulated-readers label, and the legal banner are present.
- [ ] **[author verifies]** usability on the author's terminal.

### P23 — Evaluation + live shakedown
- [ ] `sots eval` covers every goal in `system_goals.yaml` plus the grader gold set.
- [ ] **[author verifies]** One chapter goes through Acts I–VI live.
- [ ] **[author verifies]** Research doc 21 is fact-checked by SotS itself (T23.010).

### P14M — Master Grading Engine
- [ ] Every gate routes through MGE profiles; no bypass exists.
- [ ] Section F is fully measured; hard checks F1/F3/F7/F8 are proven by fixtures.
- [ ] Panel median + blocking-note behaviour; the Ch1 exemplars are loaded as level-5 anchors.
- [ ] The stability test: ±2 points and ≥ 95% identical pass/fail.
- [ ] One master answer: a repeated request without a note returns the identical output; a note creates a recorded input.

### P21A — Recheck & Reason
- [ ] It never runs automatically; the CLI/TUI require confirmation with a cost estimate.
- [ ] The reminder appears (quietly) and escalates only on material change.
- [ ] The Promise Ledger finds all Ch1 promises and flags the unassigned provocation-spiral promise.
- [ ] Challengers run blind to the Keepers; every exchange is MGE-graded; the report is ≥ 95; challengers never edit text.

### P24 — Master Audit
- [ ] Every test in the battery passes its known-good fixture and fails its known-bad fixture; non-discriminating tests are discarded.
- [ ] The battery is frozen with a hash; a foundation change triggers vN+1.
- [ ] Certification boundaries are enforced; there are no automatic rewrites; the certificate reproduces via replay.

### P25 — Writer (LOCKED)
Do not start without an explicit author instruction and a separate blueprint.
