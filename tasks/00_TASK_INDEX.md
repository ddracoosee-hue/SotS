# MASTER TASK INDEX: 620 tasks across 31 build phases (+ P25 locked)

## How to read a task

```
- [ ] **T15.063** | `rewrite/cross_checker.py` | Match each item to … → status | A test per status.
        │              │                         │                            │
        ID             file(s) to create/edit    what to build                Done when (a verifiable check)
```
- IDs are `T<phase>.<nnn>`. The numbers leave gaps on purpose (.001–.009 setup, .010+ features,
  .090 phase close), so later insertions don't renumber anything.
- Paths are relative to `src/sots/` unless they start with `config/`, `prompts/`, `tests/`,
  `eval/`, `profile`, or a root file name.
- Work **top to bottom within a phase** and **phase by phase in order**. Check the box
  (`- [x]`) when the "Done when" check passes. Checking boxes is the only edit you may make
  to these files (R-SCOPE-04).
- Tasks marked **[author verifies]** need the author. Stop and ask.
- Every phase ends with a `.090` close task: ruff + pyright + pytest green, `sots doctor`
  green (from P03), no eval regressions (from P13), and a `BUILD_LOG.md` line.

## Phases

| Phase | File | Tasks | Act | Builds |
|---|---|---|---|---|
| P00 | `P00_skeleton.md` | 32 | — | Project, config files, folder tree, CLI stubs |
| P01 | `P01_models_storage.md` | 29 | — | Every data model, SQLite schema, repo layer |
| P02 | `P02_providers.md` | 20 | — | Muse (open adapter) + local providers, routing, cache, budgets, context packs |
| P03 | `P03_agent_runtime.md` | 45 | — | **Shared agent runtime, internet/data tools, failsafes F01–F20** |
| P04 | `P04_profile_ingest.md` | 13 | I | Author profile, ingest (T04.006 is superseded by P04A) |
| P04A | `P04A_foundation.md` | 23 | all | **Book Foundation**: loader, Anchor Registry, architecture, Brief Parser, context cards F1–F6, dictation keying, protocol load, repetition, arc consistency |
| P05 | `P05_segment.md` | 12 | I | Chunking, atomic units, offset repair, summary tree |
| P06 | `P06_classify.md` | 10 | I | Classification, safety scan, review queue |
| P07 | `P07_research_tools.md` | 24 | I | Search, 10 fetchers, source tiers, citation check |
| P08 | `P08_fact_check_team.md` | 26 | I | Triage, 5 specialists, researcher/skeptic/adjudicator, VR rules, discovery capture |
| P09 | `P09_media.md` | 10 | I | Media identity, retelling, and interpretation checks |
| P10 | `P10_psyche.md` | 14 | I | Six psyche engines, board, triggers, synthesis |
| P11 | `P11_narrative_voice.md` | 10 | I | Message ledger, drift, flow, voice fingerprint |
| P11A | `P11A_voice_lab.md` | 27 | all | **Voice Lab**: `profile/voice_corpus/` intake, 120+ features, a confidence-weighted voice model, assessments that scale with the data, the Transformation Model, signature moves |
| P12 | `P12_shadow.md` | 10 | I | Shadow reflection, rubrics, goals, system audit |
| P13 | `P13_act1_orchestration.md` | 12 | I | Act I orchestration, chapter state, reports, resume/chaos |
| P13A | `P13A_brief_audit.md` | 18 | 0 | **Act 0 Brief Audit**: epistemic tiers, evidence-grade auditor, scripture/lexicon checks, per-quote translation choice, live-source attribution, consistency, audit report |
| P14 | `P14_grader.md` | 20 | all | **Quality Gate ≥ 95**, dual judges, regeneration loop, calibration |
| P14M | `P14M_master_grading_engine.md` | 16 | all | **Master Grading Engine**: F + E sections, a 9-seat professional panel, stability, one master answer |
| P14A | `P14A_block_synthesis.md` | 24 | II-D | **Block Synthesis**: dictation → block drafts in the author's voice, preservation audit, placeholders, stitch |
| P15 | `P15_rewrite_pass_a.md` | 30 | II | **Mid Polish**: Mechanic, Formatter, Line Editor, Style Analyst, Cross-Checker, Gate A |
| P16 | `P16_audience_lab.md` | 28 | III | **Audience Lab**: 4 mechanics analysts, adult persona panel, feedback loop, calibration |
| P17 | `P17_legal_chamber.md` | 23 | IV | **Legal Chamber**: 8 counsel, deliberation R0–R7, defense memos, escalation |
| P18 | `P18_discovery_expansion.md` | 25 | V | Discovery + Media scouts, Expansion Team, proposals from outputs |
| P19 | `P19_proposal_desk.md` | 14 | V | **Proposal Desk**: questions, queue, decisions, integration plan |
| P20 | `P20_master_rewrite.md` | 19 | VI | **Master Rewrite**: Weaver, Gate B, Legal Delta, audience no-regression, export |
| P21 | `P21_learning.md` | 10 | after VI | Playbook, prompt trials, learning inbox, guards |
| P21A | `P21A_reason_and_counter_council.md` | 15 | on request | **Recheck & Reason**: Author Intent Model, 6 Intent Keepers, an 8-seat Counter-Council, the Promise Ledger, the reminder |
| P22 | `P22_tui.md` | 36 | — | Every TUI screen |
| P23 | `P23_eval_live.md` | 12 | — | Full evaluation, chaos suite, live shakedown, self-fact-check of the audience research |
| P24 | `P24_master_audit.md` | 13 | milestone | **Master Audit**: sections, a verified CCAT battery (test-of-test), certification, the Master Version |
| P25 | — | — | — | **LOCKED** (free drafting Writer) |

## Cross-cutting checklists (verify at every phase close)

- [ ] Every new agent has an Agent Card with its mandatory failsafes (16 §5.2).
- [ ] Every new LLM call uses a prompt file + an output model + a routing entry.
- [ ] Every new author-facing output goes through a Quality Gate (R-GATE-01).
- [ ] Every new persisted record type has an idempotency key (F07) and a round-trip test.
- [ ] Every new internet-using agent has F03, F13, F14, and F15.
- [ ] Every new number in a report is either verified from a source or computed by code (16 §4).
- [ ] No persona or data row under 18 anywhere (R-AUD-01).
- [ ] Legal outputs carry the banner (R-LEGAL-00).
- [ ] Content agents load foundation pieces F1 + F2 (R-FOUND-01); nothing edits `profile/` directly (R-FOUND-02).
- [ ] Every judgment goes through the MGE; no agent self-grades; no reroll path exists (R-MGE-01…04).
- [ ] Author provenance markers survive to the output (R-PROV); author-final chapters are never synthesized (R-SYN-12).
- [ ] Chapter ids stay ch01–ch12; reading order comes only from book_architecture.yaml (R-FOUND-03).
- [ ] New invariants are registered in F20 where the phase introduces new cross-references.
