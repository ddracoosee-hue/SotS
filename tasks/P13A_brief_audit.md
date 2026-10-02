# P13A — Act 0: Brief Audit

**Prerequisites:** P13 (Act I works) + P04A. **Blueprint refs:** 23 §4, 25 (all), 06 §1A, 22 §9.

## Epistemic tiers
- [ ] **T13A.001** | `verify/tiers.py` | ET-01…ET-05: compute the epistemic tier from verdict + basis + retraction/replication flags. | A test per rule.
- [ ] **T13A.002** | `verify/tiers.py` | Author-tag extraction from text (`[Documented Fact]`, `[DF]`, `[PT]`, `[IE]`, `[DF/PT]`, "Evidence: Strong – …") → `tier_claimed_by_author`; mismatch findings. | Tests on the tag styles used in ch10 and ch05.
- [ ] **T13A.003** | `verify/rules.py` | Add the replication-failure detection signals (search queries "failed to replicate <finding>", meta-analysis null results) to the Academic Specialist; HEDGE assignment. | Integration test with fixtures (positivity ratio → DEBUNKED; Navon broadening → HEDGE).

## Evidence grades
- [ ] **T13A.010** | `config/agents/fact_check/evidence_grade_auditor.yaml` + prompt | The Evidence-Grade Auditor agent: finds meta-analyses/RCTs for the intervention type × outcome; applies EG-01…EG-03; outputs the verified grade + sources + suggested wording. | FakeProvider tests: a "Strong – Colossians 3:23" fixture → split into a faith basis + an empirical grade.
- [ ] **T13A.011** | `verify/evidence_grade.py` | The grade taxonomy (Strong / Moderate / Emerging / Practical / Faith-based) with deterministic caps (e.g. no meta-analysis & no RCT → max Moderate). | Tests.

## Scripture + patristics
- [ ] **T13A.020** | `research/fetchers/bible.py` | Verse lookup for the **NASB 2020** (OI-34 resolved; NASB 1995 + KJV also fetched for comparison only, 25 §5.1) from a licensed/public source; the quote-gathering helper returns the exact NASB wording + reference for synthesis (25 §5); tracks the total verses quoted for the Lockman permission check (SC-03); returns the verse text + reference. | respx tests; unknown translation → disabled cleanly.
- [ ] **T13A.021** | `research/fetchers/lexicon.py` | Greek/Hebrew term lookup from public lexicon pages (Strong's number → glosses); transliteration normalization (chrēstos ↔ chrestos ↔ χρηστός). | respx tests.
- [ ] **T13A.022** | `verify/specialists/scripture.py` | The Scripture Specialist: SCRIPTURE_QUOTE (text/reference match), SCRIPTURE_TERM (gloss support: supported / contested / unsupported), PATRISTIC_ATTRIBUTION; interpretations rated with the media ladder. SC-01 in the prompt. | Integration tests: Mt 11:30 chrēstos "well-fitting" → contested gloss; Mark 10:43 quote → TRUE.
- [ ] **T13A.023** | `verify/specialists/translation_detect.py` | Per-quote translation detector (25 §5.1): compare each scripture quote with the NASB 2020, NASB 1995 and KJV wording for the same reference → `matches: nasb2020 / nasb1995 / kjv / paraphrase / other`. Anything other than nasb2020 → a Proposal with two options: (a) switch to the NASB 2020 wording, (b) keep it with an explicit translation label. The author decides per quote; the choice is stored on the anchor. Fixtures: Ch1's Matthew 15:14 ("If the blind lead the blind…") → kjv; 1 Thess 5:23. | respx tests + the two Ch1 fixtures.
- [ ] **T13A.024** | `brief_audit/attribution.py` | Author-attested live-source attribution (25 §7, OI-37): for each anchor with author-declared provenance `live` (e.g. ch03.A02, Jordan Peterson's infinite bookshelf, heard live in Tulsa, 2024), (1) verify the event (tour stop, date, city) with the web tools; (2) scan `author_final` chapters for uses of the concept without credit (Ch1 §10) → an `attribution` Proposal with suggested wording, never an automatic edit; (3) mark later chapters' uses as callbacks. | Tests: the Ch1 §10 fixture raises exactly one attribution Proposal; an unverifiable event → the claim is kept as author-attested and labeled, not dropped.

## Consistency + audit orchestration
- [ ] **T13A.030** | `brief_audit/consistency.py` | Numeric self-consistency (e.g. "quadrupled" vs the stated start/end values), chronology checks for dated case steps, phase-label conflicts (via T04A.042), audience-address conflicts (Gen Alpha / minors addressed). | Tests on fixtures: ch06.A02, ch12.A07, ch03.A11.
- [ ] **T13A.031** | `brief_audit/runner.py` | Act 0: every anchor → the right specialist (by type/claim_kind); media anchors → 07; protocols → the Evidence-Grade Auditor; `legal:` anchors → pre-open LegalIssues (22 §9); results cached per anchor with a 30-day re-verify rule. | Integration test over a 10-anchor fixture registry.
- [ ] **T13A.032** | `brief_audit/proposals.py` | Every issue → a Proposal (kind `correction` / `brief_edit` / `evidence_grade`) graded with G-PROP ≥ 95; the `book_architecture.yaml → brief_edits_required` items also become proposals. | Test: nothing reaches the author below 95.
- [ ] **T13A.033** | `reports/brief_audit.py` | `brief_audit.md`: per chapter, anchors with verdict/tier/source; mismatches; grade audits; scripture results; legal pre-issues; consistency findings. | Snapshot test.
- [ ] **T13A.034** | `cli.py` | `sots audit-briefs [chNN|all] [--dry-run]`. | Test.
- [ ] **T13A.035** | `acts/act0.py` | Act 0 wiring + a ChapterState for all chapters ("0:done", brief version). A brief change marks the dependent acts stale. | Tests.
- [ ] **T13A.036** | `eval/gold/brief_anchors_gold.yaml` | Gold labels for 20 anchors from the registry (the author + a human fact-check). Muse ships a template with the anchor ids + empty expected verdicts. | The template exists.
- [ ] **T13A.090** | — | All green; BUILD_LOG line. | Done.
