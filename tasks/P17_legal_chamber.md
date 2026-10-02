# P17 — Legal Chamber (Act IV)

**Prerequisites:** P16. **Blueprint refs:** 22 (all), 01 R-LEGAL-00/01.

## Setup
- [ ] **T17.001** | `legal/banner.py` | The banner text constant (R-LEGAL-00) + `with_banner(markdown)`. A test that every legal renderer uses it. | Tests.
- [ ] **T17.002** | `config/agents/legal_chamber/L1…L8.yaml` + clerk/synthesizer cards | 8 counsel cards (specialty, stance, method, tools incl. internet + courtlistener, mandatory failsafes + F09) + the synthesizer. | doctor validates.
- [ ] **T17.003** | `prompts/legal/L1_defamation.v1.md` … `L8_publishing.v1.md` | One prompt per counsel: specialty checklist, stance tendency, method, jurisdiction list, the banner rule, the authority-citation rule (fetched + verified only), the output schema (Position), and the rebut-or-concede rule. | The prompts validate.
- [ ] **T17.004** | `prompts/legal/screen.v1.md` + `prompts/legal/synthesize.v1.md` | The intake screen + synthesizer prompts. | Validate.

## Intake
- [ ] **T17.010** | `legal/intake.py` | Deterministic pre-flags: person entities, allegation lexicon, court/crime lexicon, health-advice patterns, quote/lyric markers, brand names (a list), private-info patterns (addresses, phone numbers, message screenshots descriptions). | Tests per flag type.
- [ ] **T17.011** | `legal/intake.py` | The LLM screen (local) → LegalIssues with types, persons (public-figure check via a web search agent step), a preliminary risk, assigned counsel (by type + L4 + L8 always). | Integration test.
- [ ] **T17.012** | `legal/prescreen.py` | The cheap pre-screen API used by the grader (U7 / H5) on proposals and Act I units. | Test.

## Deliberation
- [ ] **T17.020** | `legal/clerk.py` | The R0–R7 state machine per issue; round limits; cycle counter; persistence of every Position. | State-machine tests.
- [ ] **T17.021** | `legal/counsel.py` | R1 blind review (the assigned counsel only; they don't see each other's drafts). | Test: the prompt inputs contain no other positions.
- [ ] **T17.022** | `legal/counsel.py` | R2 positions (all 8 read the R1 memos). | Test.
- [ ] **T17.023** | `legal/counsel.py` | R3 cross-exam: each counsel must rebut/concede the 2 most-opposed positions (by stance distance). Validator: a deferral without its own reasoning + authority → rejected. | Tests.
- [ ] **T17.024** | `legal/authorities.py` | Authority verification: fetch + excerpt-verify every cited authority; failures → the Position is invalid + the `legal_fabricated_authority` counter increments. | Tests: a fabricated case → rejected + counted.
- [ ] **T17.025** | `legal/scoring.py` | R4: grade every Position with the `legal_argument` rubric; rank the arguments. | Test.
- [ ] **T17.026** | `legal/synthesizer.py` | R5: the DefenseMemo from the top arguments; must answer every top-2-scored dissent (validator). | Tests: an unanswered top dissent → the memo fails the hard check.
- [ ] **T17.027** | `legal/endorse.py` | R6: all 8 vote; the exit rule (≥ 6/8 + no HIGH + memo G-LEGAL ≥ 95). | Tests on the boundaries (5/8 fails, 6/8 passes).
- [ ] **T17.028** | `legal/edits.py` | R7: required edits → legal_edit hunks via the Line Editor → Cross-Checker → back to R2; ≤ 3 cycles. | Integration test.
- [ ] **T17.029** | `legal/escalate.py` | BLOCKED handling: the two strongest opposing positions + options + the "Needs licensed attorney" flag; ChapterState blocked; waiver only with `--attorney-confirmed` + a reason. | Tests.

## Act IV wiring + outputs
- [ ] **T17.030** | `acts/act4.py` | Act IV: requires Gate A passed + Act III done; runs intake → deliberation per issue (issues in parallel, counsel calls concurrency-limited) → resolves or blocks. | Integration test.
- [ ] **T17.031** | `reports/sections/legal.py` | issues.md + per-issue memos with the banner; the endorsement table; dissents. | Snapshot test; banner test.
- [ ] **T17.032** | `cli.py` | `sots legal status|issue|waive`, `sots act IV`. | Tests.
- [ ] **T17.033** | `eval/legal_gold/` + `eval/run_eval.py` | Intake recall and risk agreement on 12 synthetic passages (fictional people and cases; Muse writes them and marks them synthetic). | The metrics compute.
- [ ] **T17.034** | `failsafes/f20_invariants.py` | Register `legal_authorities_verified` and `legal_banner_present`. | Tests.
- [ ] **T17.090** | — | All green; BUILD_LOG line. | Done.
