# P13 — Act I Orchestration + Reports + Core CLI

**Prerequisites:** P12. **Blueprint refs:** 02 §2, §2A; 12 §1; 16 §7.

- [ ] **T13.001** | `pipeline/stages.py` | Stage registry: name, dependencies (02 §2 table), function, resumability key. | Test: the dependency graph is valid and acyclic.
- [ ] **T13.002** | `pipeline/orchestrator.py` | Runs the stages respecting dependencies; stages 4–5 run concurrently with 6; per-stage status in Run.stage_status; the budget slice per stage. | Integration test with FakeProvider.
- [ ] **T13.003** | `acts/chapter_state.py` | The ChapterState lifecycle: acts, gate statuses, blocked reasons; `eligible_next_act(chapter)`. | Tests for every transition + a refusal on unmet prerequisites.
- [ ] **T13.004** | `acts/act1.py` | Act I = the orchestrator run + F19 canary (when > 20k words) + F20 invariants at the end → ChapterState "I:done". | Integration test.
- [ ] **T13.005** | `pipeline/dry_run.py` | A token/cost estimate per stage and per future act (II–VI, using the P02 estimates + the audience panel multiplier). | Test: 0 provider calls.
- [ ] **T13.006** | `reports/markdown.py` | report.md assembling the sections in order: summary → claims → media → psyche → messages/voice → shadow/goals; plus the "run health" section (fallbacks, degraded items, dead letters). | Snapshot test.
- [ ] **T13.007** | `reports/export.py` | report.json (all records for the run). | Test: valid JSON; it round-trips into the models.
- [ ] **T13.008** | `cli.py` | Implement `run`, `resume`, `status`, `report`, `act I`, `advance`, `chapter status`, `stop`, `doctor`, and `replay`. | CLI tests via Typer's CliRunner.
- [ ] **T13.009** | `tests/integration/test_act1_resume.py` | Kill mid-stage 5 → resume → completes; the call count proves no redo. | Passes.
- [ ] **T13.010** | `tests/chaos/test_kill_random.py` | 20 random kill points → resume → a final DB snapshot equal to the uninterrupted run (excluding timestamps). | Passes with `-m chaos`.
- [ ] **T13.011** | `eval/run_eval.py` | The first version: the gold-set metrics for extraction, classification, and verdicts (14 §4). | Runs on a small sample gold set (3 passages Muse writes as a placeholder, marked `synthetic_placeholder`).
- [ ] **T13.090** | — | All green; BUILD_LOG line. | Done.
