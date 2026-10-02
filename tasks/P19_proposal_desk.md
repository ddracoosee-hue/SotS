# P19 — Proposal Desk (Act V: author decisions)

**Prerequisites:** P18. **Blueprint refs:** 18 (all), 17 G-PROP, 01 R-GATE-01.

- [ ] **T19.001** | `proposals/builder.py` | A common builder that assembles a Proposal from any producer draft; computes the priority; attaches the legal pre-screen risks (P17) and quick-pitch audience scores (P16). | Tests.
- [ ] **T19.002** | `proposals/question_check.py` | The validator: concrete element required (a work/character/case/number/unit quote ≤ 25 words); leading-question detection (a phrase list: "doesn't this", "don't you feel", "isn't it"); 2–5 questions; ≥ 1 required; the required patterns for media_* kinds (≥ 2 of the 5). | Tests: generic rejected; leading rejected; valid accepted.
- [ ] **T19.003** | `proposals/grading.py` | Every proposal → the regeneration loop with the `proposal` rubric (G-PROP ≥ 95); below-bar → archive. | Integration test.
- [ ] **T19.004** | `proposals/dedup.py` | Merge proposals about the same work/case/concept before grading (entity + title similarity). | Test.
- [ ] **T19.005** | `proposals/queue.py` | max_open (default 7), priority ordering, holding proposals for chapters in Act IV, the defer countdown. | Tests.
- [ ] **T19.006** | `proposals/desk.py` | present/decide API: accept (placement + mode + required answers), modify (answers → producer regenerate → re-grade), defer, reject (reason enum). | Tests per decision path.
- [ ] **T19.007** | `proposals/chat.py` | Chat with the proposing agent (Dialogist runtime), grounded in the proposal evidence; a changed proposal → re-grade before re-display. | Test.
- [ ] **T19.008** | `proposals/plan.py` | accept → IntegrationPlanItem (with the author answers stored as AUTHOR-origin material; R-EXP-11 adds them to the concept graph). | Tests.
- [ ] **T19.009** | `proposals/learning_hooks.py` | Decisions → grader calibration records + reject-reason summaries for the producers' "avoid" lists (as proposed LearningChanges, LR-01). | Tests.
- [ ] **T19.010** | `acts/act5.py` (desk part) | Act V completes for a chapter when the queue for that chapter is empty (all decided or deferred) **or** the author marks "done deciding". | Test.
- [ ] **T19.011** | `cli.py` | `sots proposals list|show|decide|archive`. | Tests.
- [ ] **T19.012** | `reports/sections/proposals.py` | A decisions summary per chapter (accepted/rejected with reasons). | Snapshot test.
- [ ] **T19.013** | `eval/proposal_gold/` + `eval/run_eval.py` | Usability agreement between the grader and the author's decisions. | The metric computes.
- [ ] **T19.090** | — | All green; BUILD_LOG line. | Done.
