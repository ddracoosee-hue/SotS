# P14M — Master Grading Engine (MGE)

**Prerequisites:** P14 (gate mechanics). **Build this BEFORE P14A** (every later team grades through it).
**Blueprint refs:** 27 (all), 17 (mechanics), 01 §D5.

## Config + models
- [ ] **T14M.001** | `config/mge.yaml` | Sections F (F1–F9) and E (E1–E8): weights, floors, hard checks, panel seats per criterion, and a profile per artifact type (proposal, block_draft, rewrite_hunk, legal_memo, audience_brief, research_report, challenge, deliberation, reasoning_report, master_audit). | Loader test; weights sum to 1 per section.
- [ ] **T14M.002** | `models/mge.py` | SectionScore, SeatJudgment, BlockingNote, MasterGrade (extends GradeRecord: F, E, MASTER, mge_version, panel notes). | Round-trip tests.

## Section F (factual): measured
- [ ] **T14M.010** | `mge/section_f.py` | F1–F9 computed from verdicts, evidence, tiers, provenance markers, NASB checks, and the consistency results. No LLM. | A test per criterion with hand-computed values.
- [ ] **T14M.011** | `mge/section_f.py` | Hard checks F1 (no uncorrected FALSE), F3 (100% citation integrity), F7 quotes (NASB exact), F8 (belief/source framing). | A pass/fail fixture per hard check.

## Section E (emotional)
- [ ] **T14M.020** | `mge/section_e.py` | Measured parts: E2 from the Audience scorecard + journey spec, E4 safety metrics, E5 reactance indices, E6 style similarity, E7 cohort metrics (calibrated). | Tests.
- [ ] **T14M.021** | `mge/section_e.py` | Judged parts via the panel: E1 (against the AIM entry; provisional flag if unconfirmed), E3, E4 judged, E8 (any violation → hard fail). | FakeProvider tests.

## Professional Perspective Panel
- [ ] **T14M.030** | `prompts/mge/panel/P1_dev_editor.v1.md` … `P9_target_reader.v1.md` | Nine seat prompts, each with its checklist, anchors, the "never impersonate real people" rule, and the JSON schema. | The prompt loader validates them.
- [ ] **T14M.031** | `mge/panel.py` | Run the applicable seats per criterion at temperature 0; median aggregation; a seat ≤ 2 with a cited reason → BlockingNote; an independent recheck of that seat (`mge.blocking_recheck`). | Tests: the median; a blocking note raised and cleared by a non-reproducing recheck.
- [ ] **T14M.032** | `eval/mge_calibration/` + `mge/exemplars.py` | Exemplar library: Ch1 excerpts (≤ 300 words each) as level-5 anchors for E1/E3/E6 and P1/P2; placeholders for levels 2–4 (the author supplies or approves them); versioned. | Loader test; the excerpt-length guard.

## Master score, stability, integration
- [ ] **T14M.040** | `mge/master.py` | MASTER = 100 × (wF·F + wE·E)/5; the PASS rule (≥ 95 + hard checks + floors + no unresolved blocking note). | Boundary tests.
- [ ] **T14M.041** | `mge/stability.py` + `cli.py` | `sots mge stability`: re-grade 20 cached artifacts with the cache disabled; ±2 points and ≥ 95% identical pass/fail, or a health alert + frozen rubric version. | Test with a FakeProvider that injects small noise.
- [ ] **T14M.042** | `grader/grader.py` | Route every gate (17 §1) through MGE profiles; the 17 rubrics become profiles; GradeRecords carry mge_version. | The existing P14 tests still pass through the MGE.
- [ ] **T14M.043** | `agents/base.py` + `agents/cards.py` | R-MGE-01/02: a card without a profile may not produce author-facing or text-changing output (doctor check); no bypass flag exists (a test greps for one). | Tests.
- [ ] **T14M.044** | `mge/revision_notes.py` | R-MGE-04: "regenerate" is not a command. `revise --note "…"` records a RevisionNote input, the pipeline re-runs, and the new master output is graded. The same input state returns the cached master output. | Tests: no-note re-request → identical output; note → a new recorded input.
- [ ] **T14M.045** | `tui/screens/grade_inspector.py` (spec, built in P22) | Grade Inspector: section scores, criterion evidence, panel notes, failure reasons. | Registered in the P22 list.
- [ ] **T14M.090** | — | All green; BUILD_LOG line. | Done.
