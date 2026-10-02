# P20 — Rewrite Pass B + Legal Delta + Master Export (Act VI)

**Prerequisites:** P19. **Blueprint refs:** 19 §4–§6, 22 §7, 20 §5.3, 10, 17 G-HUNK-B.

## Pass B agents
- [ ] **T20.001** | `config/agents/rewrite_pass_b/*.yaml` | Cards: weaver, master_rewriter, mechanic_b, formatter_b, style_analyst_b, cross_checker_b. | doctor validates.
- [ ] **T20.002** | `prompts/rewrite/weave.v1.md` + `rewrite/weaver.py` | One woven insert per IntegrationPlanItem, at its placement, in its mode; personal content only from author answers or existing units; facts only from the plan evidence with endnotes; the length ≤ word_estimate × 1.25; quotes ≤ 300 chars; no lyrics. | A test per rule; the invented-memory fixture is caught.
- [ ] **T20.003** | `rewrite/weaver.py` | Each woven insert is graded individually (G-HUNK-B ≥ 95) via the regeneration loop. | Test.
- [ ] **T20.004** | `prompts/rewrite/master.v1.md` + `rewrite/master.py` | The whole-chapter flow pass: transitions around the inserts, the final audience brief items, the remaining legal edits; the edit budget 0.35 (inserts excluded); strong lines protected. | Tests.
- [ ] **T20.005** | `rewrite/mechanic.py`, `rewrite/formatter.py` | Pass B mode: the final proof + endnote numbering per chapter + bibliography assembly (Chicago notes default; OI-25). | Tests: endnote numbering is sequential; every marker has a note.

## Gate B + downstream checks
- [ ] **T20.010** | `rewrite/gates.py` | `gate_b`: all of Gate A + chapter voice ≥ 0.88 + inserts ≥ 0.80 + endnotes resolve + 0 `[[VERIFY]]` (or waived). | A test per condition.
- [ ] **T20.011** | `legal/delta.py` | Legal Delta scope selection (woven hunks, hunks touching LegalIssue units, new pre-screen flags); the panel (relevant counsel + L4 + L8, minimum 3); exit ≥ 2/3 + memo ≥ 95 + no HIGH. | Tests.
- [ ] **T20.012** | `legal/delta.py` | Re-validate resolved memos whose units changed (entailment of text_position) → re-open on failure. | Test.
- [ ] **T20.013** | `acts/act6.py` | Audience no-regression: primary metrics ≥ the Act III final − 0.3, else Gate B fails with the regressions listed. | Test.
- [ ] **T20.014** | `acts/act6.py` | The Shadow final grade on the Pass B revision; hard goals block unless waived. | Test.
- [ ] **T20.015** | `acts/act6.py` | Every remaining hunk is graded G-HUNK-B; below-bar hunks are dropped (reverted to the parent text), and the drop is logged. | Test.

## Author review + export
- [ ] **T20.020** | `rewrite/review.py` | The hunk review API: accept/reject/undo; bulk accept by change type; the decisions applied → Revision B-final; a Cross-Check re-run on the final text. | Tests.
- [ ] **T20.021** | `acts/act6.py` | The full Act VI flow of 19 §4 with every gate; ChapterState "VI:done" only after the author review. | Integration test.
- [ ] **T20.022** | `reports/manuscript.py` | Export manuscript.md + manuscript.docx (python-docx styles from formatting.yaml: headings, body, block quotes, endnotes section). | Tests: the docx opens and heading/paragraph counts match.
- [ ] **T20.023** | `reports/manuscript.py` | endnotes.md, bibliography.md, sources.json, change_log.md, fact_check_appendix.md, legal_memos/ (with the banner), audit_bundle.json. | A test checks each file exists and parses.
- [ ] **T20.024** | `cli.py` | `sots act VI`, `sots export <chapter|all>`. | Tests.
- [ ] **T20.025** | `failsafes/f20_invariants.py` | Register `export_consistency`: every endnote in the manuscript maps to an Evidence in sources.json; every legal memo referenced exists. | Test.
- [ ] **T20.026** | `tests/integration/test_acts_1_to_6.py` | A full fixture chapter through Acts I–VI with FakeProvider, scripted author decisions, and scripted hunk review. | Passes.
- [ ] **T20.090** | — | All green; BUILD_LOG line. | Done.
