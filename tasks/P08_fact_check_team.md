# P08 — Fact-Check Team

**Prerequisites:** P07. **Blueprint refs:** 06 §4–§9, 16.

## Agent cards + prompts
- [ ] **T08.001** | `config/agents/fact_check/*.yaml` | Cards: triage, stats, courts, academic, social, quotes, researcher, skeptic, adjudicator, discovery_scout, media_scout (the media scout is used in P18). | `sots doctor` validates all of them.
- [ ] **T08.002** | `prompts/fact_check/*.v1.md` + `prompts/verify/*.v1.md` | A prompt per agent. Each includes: its role, the rules it must follow (cite the R-/VR- ids), the output schema description, the `<source>`/`<observation>` data warning (R-EXP-04), and 1 worked example. | The prompt loader validates all of them.

## Triage + specialists
- [ ] **T08.010** | `verify/triage.py` | Priority = message priority weight × centrality (the unit is `states`/`supports_with_evidence` in the ledger if available, else 1) × preliminary risk; assigns the specialist by claim_kind; per-unit budget slices. | Test: ordering + assignment.
- [ ] **T08.011** | `verify/specialists/stats.py` | Agent: find the publisher → fetch the table → parse_table → compute the figure → fill `value_found`, `year_found`, `population`, `place`, `original_publisher`. | An integration test with a fixture CSV/HTML table: the recomputed value matches.
- [ ] **T08.012** | `verify/specialists/courts.py` | Agent: CourtListener search → docket → opinion → procedural history → the claim_specific legal fields. | Integration test with fixtures.
- [ ] **T08.013** | `verify/specialists/academic.py` | Agent: OpenAlex/Crossref → the design, sample size, retraction, and finding fields. | Integration test.
- [ ] **T08.014** | `verify/specialists/social.py` | Agent: fact-check lookups + searches → `event_occurred` / `content_true` / `debunked_by`. | Integration test.
- [ ] **T08.015** | `verify/specialists/quotes.py` | Agent: traces the earliest verifiable source; `quote_found` / `speaker_found` / `context`. | Integration test with a misattribution fixture.
- [ ] **T08.016** | `verify/specialists/handoff.py` | SpecialistFindings → the Researcher input; the researcher's discards must include a reason. | Test.

## Core three roles
- [ ] **T08.020** | `verify/researcher.py` | Agent producing ResearcherOut; evidence is excerpt-verified before the Skeptic sees it. | Test.
- [ ] **T08.021** | `verify/skeptic.py` | Agent producing SkepticOut, with the 7 attack questions of 06 §4.2 in the prompt. | Test.
- [ ] **T08.022** | `verify/adjudicator.py` | Agent producing AdjudicatorOut; the postcondition: every HIGH objection is referenced (fuzzy match on its first 40 characters). | Test: a missing reference → retry.

## Rules + confidence
- [ ] **T08.030** | `verify/rules.py` | Implement VR-GEN-01…07 as pure functions returning RuleCheck. | One test file per rule group; pass and fail cases for each rule.
- [ ] **T08.031** | `verify/rules.py` | VR-STAT-01…04. | Tests.
- [ ] **T08.032** | `verify/rules.py` | VR-LAW-01…03. | Tests.
- [ ] **T08.033** | `verify/rules.py` | VR-ACA-01…03. | Tests.
- [ ] **T08.034** | `verify/rules.py` | VR-SOC-01…02. | Tests.
- [ ] **T08.035** | `verify/rules.py` | VR-QUO-01…02. | Tests.
- [ ] **T08.036** | `verify/rules.py` | `apply_caps(proposed, checks) -> final` (the min by strength); fiction evidence → CONTEXT before the other rules run. | Tests, including a TRUE capped by 3 rules.
- [ ] **T08.037** | `verify/confidence.py` | The 06 §7 formula. | Tests against 3 hand-computed cases.
- [ ] **T08.038** | `verify/labels.py` | The author-facing label mapping (06 §1 table). | Tests covering every row.

## Stage wiring
- [ ] **T08.040** | `verify/verify_stage.py` | For each checkable unit: triage → specialist → planner → candidates → fetch → researcher → skeptic → adjudicator → rules → confidence → VerdictRecord. Resumable per unit; units are processed concurrently with a semaphore. | Integration test over a fixture document.
- [ ] **T08.041** | `verify/discovery_capture.py` | DiscoveryNote emission hook for every fact-check agent (≤ 3 per unit, verified evidence only, dedup). | Tests.
- [ ] **T08.042** | `reports/sections/claims.py` | The Markdown claim section per 06 §8. | Snapshot test.
- [ ] **T08.043** | `cli.py` | `sots claims <run_id> [--verdict] [--kind]` with the author-facing labels. | Test.
- [ ] **T08.090** | — | All green; BUILD_LOG line. | Done.
