# P15 — Rewrite Pass A (Act II: Mid Polish)

**Prerequisites:** P14. **Blueprint refs:** 19 §1–§3, §5, §7; 01 R-REW-01…03.

## Revisions infrastructure
- [ ] **T15.001** | `rewrite/revisions.py` | Create a Revision from a parent + hunks: apply the hunks in offset order, write a new file (atomic), sha256, a `.diff` (difflib unified). | Tests: overlapping hunks rejected; order independence.
- [ ] **T15.002** | `rewrite/anchor.py` | Re-anchor the units through the hunks → `revision_offsets[rev_id]`; units deleted by a hunk are marked `removed_in=rev_id`. | Tests: offsets are correct after insert/delete/replace.
- [ ] **T15.003** | `failsafes/f20_invariants.py` | Register `revision_offset_integrity`: for every unit present in a revision, the revision text at its offsets == the unit text (or the hunk-modified text is recorded). | Test.
- [ ] **T15.004** | `rewrite/edit_budget.py` | Per-paragraph token change ratio (difflib SequenceMatcher on tokens); rejects hunks over the budget. | Tests.

## Style Guide
- [ ] **T15.010** | `prompts/rewrite/style_guide.v1.md` + `rewrite/style_guide.py` | Build the StyleGuide from the samples + fingerprint; cached by the source hash; version bump on change. | Test.
- [ ] **T15.011** | `rewrite/style_guide.py` | Author approval state; Pass A refuses to start with an unapproved guide (ChapterState blocked reason "style_guide_unapproved"). | Test.
- [ ] **T15.012** | `cli.py` | `sots style-guide build|show|approve` (approval opens `$EDITOR` on a YAML export, then re-imports it). | Test with a fake editor.

## Mechanic
- [ ] **T15.020** | `agents/tools/languagetool.py` | httpx client to `/v2/check` (language, text, disabledRules from config); maps matches → candidate hunks (offset, length, replacements, rule id, category). | respx test.
- [ ] **T15.021** | `rewrite/mechanic.py` | Filter: drop matches that touch protected terms; drop the STYLE/REDUNDANCY categories (the Mechanic doesn't rephrase). | Tests.
- [ ] **T15.022** | `prompts/rewrite/mechanic_adjudicate.v1.md` + `rewrite/mechanic.py` | The LLM adjudicator accepts/rejects each remaining candidate against the Style Guide (intentional_patterns); outputs hunks of type spelling/grammar/punctuation. | Test: an intentional fragment is kept.
- [ ] **T15.023** | `rewrite/mechanic.py` | Degraded mode when LanguageTool is down (F03 open): an LLM-only spelling/grammar pass, conservative, flagged degraded. | Test.

## Formatter
- [ ] **T15.030** | `rewrite/formatter.py` | Deterministic rules from formatting.yaml: quotes, dashes, ellipses, number style (Chicago), headings, scene breaks, endnote markers. Style Guide overrides are logged. | A test per rule; idempotency test.
- [ ] **T15.031** | `prompts/rewrite/format_structure.v1.md` + `rewrite/formatter.py` | An LLM structure pass: paragraph breaks and heading detection only (the words are unchanged; this is verified by a token-equality check ignoring whitespace). | Test: any word change → the hunk is rejected.

## Line Editor
- [ ] **T15.040** | `prompts/rewrite/line_edit.v1.md` + `rewrite/line_editor.py` | Per paragraph with the Style Guide + neighbours: clarity/flow hunks; applies only the authorized fact corrections (19 §3.1) with evidence_ids; inserts `[[VERIFY]]` markers for UNSUPPORTED/UNVERIFIABLE units; ≤ 1 bridge sentence per flow break. | Tests for each rule.
- [ ] **T15.041** | `rewrite/line_editor.py` | `apply_reports(style_report, cross_check_report)` mode: revise only the failing hunks based on fix_requests. | Test.
- [ ] **T15.042** | `rewrite/personal_content_guard.py` | Detects new first-person experiential claims ("I remember", "when I was", "I felt") in `after` that are not in `before` or the author answers → reject (R-REW-02). | Tests.

## Meaning check
- [ ] **T15.050** | `rewrite/meaning.py` | The deterministic part: numbers, named entities (a capitalized-sequence heuristic + the entities from units), and negations preserved unless the hunk is authorized. | Tests: a negation flip is caught; a number change is caught; an authorized correction passes.
- [ ] **T15.051** | `prompts/rewrite/entailment.v1.md` + `rewrite/meaning.py` | The LLM entailment check (same_meaning, stance_changed, lost_content). | Tests.

## Style Analyst + Cross-Checker
- [ ] **T15.060** | `config/agents/rewrite_pass_a/*.yaml` | Cards: mechanic_a, formatter_a, line_editor_a, style_analyst_a, cross_checker_a (with the mandatory failsafes incl. F11). | doctor validates.
- [ ] **T15.061** | `prompts/rewrite/style_report.v1.md` + `rewrite/style_analyst.py` | StyleReport: the fingerprints before/after, voice similarity (P11), per-hunk local similarity, protected terms intact, tone shift (computed with the P16 tonality metrics once available; placeholder zeros until P16, marked), drift notes, fix requests. | Tests.
- [ ] **T15.062** | `rewrite/cross_checker.py` | Checkable item extraction (numbers, dates, names, titles, quotes, cases, studies, media details, endnotes) via regex + entities + an LLM listing pass. | Tests on a fixture paragraph with 12 known items.
- [ ] **T15.063** | `rewrite/cross_checker.py` | Match each item to its origin unit + VerdictRecord/Evidence → status (match / correctly_corrected / drifted / new_unverified_claim / lost_attribution / stale_source). | A test per status.
- [ ] **T15.064** | `rewrite/cross_checker.py` | Internet re-verification: re-fetch the cited sources (cache-aware, TTL override `rewrite.recheck_ttl_days`, default 7), re-run excerpt verification, and search for retraction/correction notices for academic/legal items. | respx tests: a changed page → stale_source; a retraction found → flagged.
- [ ] **T15.065** | `rewrite/cross_checker.py` | pass_rate computation + the CrossCheckReport. | Test.

## Gate A + Act II
- [ ] **T15.070** | `rewrite/gates.py` | `gate_a(revision) -> GateResult` with every condition of 19 §3.2. | Tests: each condition failing alone.
- [ ] **T15.071** | `acts/act2.py` | Act II flow: Mechanic → Formatter → Line Editor → (Style ∥ Cross-check) → Gate A → loop ≤ 3 → escalate (ChapterState blocked reason "pass_a_needs_author"). | Integration test with FakeProvider: pass on loop 2; escalation on loop 3.
- [ ] **T15.072** | `acts/act2.py` | Optional author review mode (`rewrite.pass_a.author_review`): hunks graded with G-HUNK-A before being shown. | Test.
- [ ] **T15.073** | `cli.py` | `sots act II <chapter>`, `sots revisions list|diff`, `sots hunks review` (terminal accept/reject). | Tests.
- [ ] **T15.074** | `eval/rewrite_gold/` + `eval/run_eval.py` | Mechanic precision/recall, protected-terms preservation, drift escapes (the author fills the gold set; placeholder items marked synthetic). | The metrics compute.
- [ ] **T15.090** | — | All green; BUILD_LOG line. | Done.
