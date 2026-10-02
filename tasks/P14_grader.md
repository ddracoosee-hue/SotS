# P14 — Quality Gate Grader

**Prerequisites:** P13. **Blueprint refs:** 17 (all), 01 R-GATE-01/02.

## Rubric engine
- [ ] **T14.001** | `grader/rubrics.py` | Load grader.yaml → the typed Rubric (criteria with type/weight/floor/anchors; hard checks by id); validates the weights sum to 1.0. | Tests.
- [ ] **T14.002** | `grader/hard_checks.py` | A registry of the hard-check functions by id: H1–H6 (proposal), the hunk checks, the report checks, the memo checks, the brief checks. Each returns (passed, reason). | A test per hard check (pass + fail).
- [ ] **T14.003** | `grader/measured.py` | A registry of the measured-criterion functions (R1, R2, R4, U1-measured part, U3, U4, U5, U7, and the hunk/report/memo/brief measured criteria). Each returns a 0–5 score + an evidence string. | A test per function with hand-computed expectations.
- [ ] **T14.004** | `grader/score.py` | The weighted score 0–100; the PASS rule (threshold + floors + hard checks). | Tests: the boundary at exactly 95; one floor failure fails despite a high score.

## Judges
- [ ] **T14.010** | `prompts/grader/judge_strict.v1.md`, `judge_reader.v1.md`, `judge_tiebreak.v1.md` | The judge prompts: anchors per criterion, a required citation of evidence, JSON output, **no knowledge of the attempt number**. | The prompt loader validates them.
- [ ] **T14.011** | `grader/judges.py` | Runs judges A and B (different routing tasks), takes the min per criterion; a gap ≥ 2 → judge C → the median. | Tests: min logic; tiebreak trigger; median.
- [ ] **T14.012** | `grader/feedback.py` | Builds `feedback_for_generator` from the failing criteria + hard checks; the validator rejects vague feedback (a banned vague-phrase list + a requirement for a concrete object: a unit id, source, number, or placement). | Tests.
- [ ] **T14.013** | `grader/grader.py` | `grade(artifact, rubric_id) -> GradeRecord`, persisted. | Integration test.

## Regeneration loop
- [ ] **T14.020** | `grader/loop.py` | `regeneration_loop(producer, inputs, rubric, max_attempts, plateau_rule)` → (artifact, grade, outcome ∈ {passed, below_bar, plateau}). | Three tests: pass on attempt 2; below-bar after 4; plateau stop.
- [ ] **T14.021** | `grader/loop.py` | GR-01: the producer's prompt input receives only the feedback strings (assert that no rubric anchor text or numbers are present). | Test.
- [ ] **T14.022** | `grader/loop.py` | GR-02: the judge input contains no attempt/prior-score fields. | Test.
- [ ] **T14.023** | `grader/loop.py` | GR-05: a > 30% content-length drop between attempts → a reviewer flag on the GradeRecord. | Test.
- [ ] **T14.024** | `grader/archive.py` | The below-bar archive (all attempts + grades); `promote(id)` logs an override. | Tests.
- [ ] **T14.025** | `agents/base.py` | Replace the P03 grading stub with the real loop. | The demo agent with a rubric regenerates until it passes.

## Calibration + health
- [ ] **T14.030** | `grader/calibration.py` | The health signals (too lenient/too strict/disagreement/reject clusters) over a rolling window. | Tests on a synthetic history.
- [ ] **T14.031** | `grader/calibration.py` | Health alert → a LearningChange proposal (status "proposed") for a rubric adjustment. | Test.
- [ ] **T14.032** | `eval/grader_gold/README.md` + `eval/run_eval.py` | The judge-agreement metric vs hand grades (the author fills the gold set later; Muse ships 3 placeholder items marked synthetic). | The metric computes.
- [ ] **T14.033** | `cli.py` | `sots grader health`. | Test.
- [ ] **T14.034** | `failsafes/f20_invariants.py` | Register the invariant `no_below_bar_presented`: every item with status presented/queued for the author has a passing GradeRecord. | Test with a planted violation.
- [ ] **T14.090** | — | All green; BUILD_LOG line. | Done.
