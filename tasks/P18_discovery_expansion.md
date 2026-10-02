# P18 — Discovery Scouts + Expansion Team (Act V producers)

**Prerequisites:** P17. **Blueprint refs:** 06 §9.2–§9.4, 11 (all incl. §8), 18 §1, §3.

## Discovery + Media scouts
- [ ] **T18.001** | `discovery/notes.py` | Load, dedupe, and rank the DiscoveryNotes per chapter (relevance × novelty × tier). | Tests.
- [ ] **T18.002** | `discovery/discovery_scout.py` | Agent: top N notes → ≤ 3 strengthening searches each → Proposal drafts (kinds: stronger_evidence, correction, case_study, statistic, counterpoint) with the 18 §3 question patterns. | FakeProvider integration test.
- [ ] **T18.003** | `discovery/media_scout.py` | Agent: theme-based searches → candidate works → resolve via 07 §1 → established readings via 07 §2 → hard filters (resolved, sourced, not already cited, not excluded) → media_echo/contrast/context proposals. | Tests: each filter rejects its fixture.
- [ ] **T18.004** | `profile/loader.py` | Support `media_exclusions` in book.md. | Test.

## Expansion Team (from 11)
- [ ] **T18.010** | `expand/cartographer.py` + prompts concepts/merge/link | Concept extraction per chunk; deterministic merge (fuzzy ≥ 85 or ≥ 50% shared units/entities); ambiguous pairs → a batched LLM merge; inferred edges ≤ 3 per concept. | Tests: duplicates merge; distinct concepts stay separate.
- [ ] **T18.011** | `expand/graph_metrics.py` | Degree → hubs; cross-chapter connectors → bridges; orphans; maturity (seed/developing/developed). | Tests on a hand-built graph.
- [ ] **T18.012** | `expand/explorer.py` + prompt propose | The 6 recipes (11 §4.2) as deterministic trigger detectors + the LLM thread drafting. | A test per recipe trigger.
- [ ] **T18.013** | `expand/explorer.py` + prompt write_brief | ResearchBrief generation into the fixed template (R-EXP-05). | Test: a free-form system prompt in the output → rejected.
- [ ] **T18.014** | `expand/critic.py` + prompt critic | CriticScore for threads/reports/integrations; relevance < min_relevance → reject (R-EXP-07). | Tests.
- [ ] **T18.015** | `expand/synthesis_critic.py` | The Synthesis Critic (11 §8.1): an intellectual-depth check for high-level adult readers (rejects pop-psychology framings; demands mechanisms/limits). | Test.
- [ ] **T18.016** | `expand/lead.py` | The deterministic Lead: the thread queue, the approval gate (R-EXP-06), per-thread budgets, concurrency. | Test: research never starts without approval.
- [ ] **T18.017** | `expand/deep_researcher.py` + prompts queries/read | The multi-round loop (11 §4.3) with the 4 stop conditions, novelty, answered/partial/open marking, and leads filtered by the critic. | Four stop-condition tests.
- [ ] **T18.018** | `expand/report_writer.py` + prompt report | The DeepResearchReport from notes only. | FakeProvider test.
- [ ] **T18.019** | `expand/report_validator.py` | R-EXP-03 statement removal; id existence; a non-empty counter section; the rules pass on key statements with labels. | Tests.
- [ ] **T18.020** | `expand/report_writer.py` | Grade the reports with G-REPORT ≥ 95 via the regeneration loop. | Test.
- [ ] **T18.021** | `expand/retrieval.py` | BM25 over units + notes + reports + author answers (no vector DB). | Tests.
- [ ] **T18.022** | `expand/dialogist.py` + prompts dialogue/chat | Margin mode (≤ 1 note per 3 units; deterministic echo detection first) + chat mode (grounded; factual sentences cite notes; SYSTEM-labeled reflections; "research this" → a proposed thread). | Tests.
- [ ] **T18.023** | `expand/integrator.py` + prompt integrate | IntegrationBrief (outline only, R-EXP-08 guard: no paragraph > 60 words). | Test.
- [ ] **T18.024** | `expand/thread_scout.py` | Incremental re-run of the Explorer recipes for the concepts touched by newly ingested documents. | Test.
- [ ] **T18.025** | `expand/cross_chapter_planner.py` | Accepted concept_bridge → setup/payoff IntegrationPlanItems across chapters. | Test.
- [ ] **T18.026** | `expand/to_proposals.py` | Convert expansion outputs into Proposals (11 §8 table) with the required questions, ≥ 2 placements/modes; never raw dumps. | Tests per kind.
- [ ] **T18.027** | `failsafes/f13_injection.py` | An injection fixture test specific to deep research: a page with embedded instructions → no schema/behaviour change. | Passes.
- [ ] **T18.028** | `acts/act5.py` (producers part) | Act V producers: scouts + expansion run in the background after Act I; outputs go to the grader → the desk queue (P19). | Integration test (up to the grader).
- [ ] **T18.029** | `cli.py` | `sots expand map|propose|approve|research|dialogue|integrate`. | Tests.
- [ ] **T18.090** | — | All green; BUILD_LOG line. | Done.
