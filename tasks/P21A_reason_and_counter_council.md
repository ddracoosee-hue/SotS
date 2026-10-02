# P21A — Recheck & Reason: Intent Keepers + Counter-Council

**Prerequisites:** P21 (and P14M, P04A). **Blueprint refs:** 26 (all), 27, 23, `profile/manuscript/ch01_analysis.md §5`.

## Author Intent Model
- [ ] **T21A.001** | `models/reason.py` | IntentEntry, AuthorIntentModel, StructureFinding, Challenge, Exchange (response + rebuttal + outcome), ReasoningReport, Promise (text, source location, target chapter, status). | Round-trip tests.
- [ ] **T21A.002** | `prompts/reason/intent_cartographer.v1.md` + `reason/aim.py` | Build the AIM from the foundation (brief purposes, old→new beliefs, messages, arc roles) + the author-final chapters; write `profile/intent_model.yaml` only via a FoundationChange; entries start `confirmed_by_author: false`. | FakeProvider test.
- [ ] **T21A.003** | `reason/promises.py` | The Promise Ledger: extract forward promises from author-final chapters and drafts (patterns: "later in this book", "in the next chapter", "I'll come back to", "I'll defend it later"); seed from ch01_analysis §5; assign target chapters from the architecture; unassigned → HIGH finding. | Tests on Ch1: all 10 ledger items found, including the provocation-spiral promise as unassigned.

## Intent Keepers
- [ ] **T21A.010** | `config/agents/reason/keeper_*.yaml` + `prompts/reason/keeper_*.v1.md` | Six Keeper agents (26 §3) with foundation pieces F1–F6 + the AIM slice. | doctor validates.
- [ ] **T21A.011** | `reason/keepers.py` | Run the Keepers in parallel on the scope → StructureFindings (each cites intent entries + units). | Integration test.

## Counter-Council
- [ ] **T21A.020** | `config/agents/reason/council_C1…C8.yaml` + prompts | Eight challenger seats (26 §4), each with a distinct worldview/checklist, internet access for empirical challenges (R-TRUTH-02), and SC-01 respected by C5. | doctor validates.
- [ ] **T21A.021** | `reason/council.py` | Challengers run blind to the Keepers' R1 output → Challenges. | Test: the prompt inputs contain no StructureFindings.

## Deliberation protocol
- [ ] **T21A.030** | `reason/protocol.py` | R0–R7: MGE `challenge` grading (drop < 70) → Keeper response (defend/concede/reframe) → one rebuttal → MGE `deliberation` grading → outcome (defended/revise/open) → synthesis graded `reasoning_report` ≥ 95. | Integration test with scripted fixtures for each outcome.
- [ ] **T21A.031** | `reason/protocol.py` | Round caps (F04), no text edits by challengers, conceded points → Proposals (G-PROP). | Tests.
- [ ] **T21A.032** | `reason/report.py` | The Reasoning Report (26 §6) + a diff vs the previous report; history stored. | Snapshot test.

## Triggering + reminder (R-REASON-01…03)
- [ ] **T21A.040** | `cli.py` | `sots reason [--scope book|phase|chNN] [--focus structure|ideas|both] [--dry-run]`; always shows the cost estimate + asks for confirmation. | Test: never runs without confirmation; no act calls it.
- [ ] **T21A.041** | `reason/reminder.py` | Material-change detection since the last run (≥ 10% of units changed, a reorder, new chapters) → a reminder state for the TUI/CLI; the one-line tip after `sots act VI` / `sots export`. | Tests.
- [ ] **T21A.042** | `README.md` + `MUSE_START_HERE.md` | Add the author note: *"Recheck & Reason is available whenever you want the book's structure and ideas re-examined by the Intent Keepers and the Counter-Council: `sots reason` (or the TUI button). It never runs on its own."* | Text present in both.
- [ ] **T21A.043** | `tui/screens/reason.py` + `tui/screens/intent.py` (specs, built in P22) | The Recheck & Reason screen (run, report, challenges with outcomes, promise ledger) and the Intent screen (confirm/edit AIM entries). | Registered in the P22 list.
- [ ] **T21A.090** | — | All green; BUILD_LOG line. | Done.
