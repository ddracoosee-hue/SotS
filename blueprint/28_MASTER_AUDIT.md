# 28 — MASTER AUDIT (the end section: producing the absolute master version)

**Purpose:** a final, whole-book audit that combines every parameter in SotS and tests the
manuscript against a **verified test battery built for cross-analysing concepts and ideas**.
Passing it produces the **Master Version** of *The Subject of the Self*.

**Status:** this is the **last build phase** (P24). It is a **low-frequency tool**: run at
milestones (a full draft, pre-submission, pre-publication), not in daily work. It is the most
expensive run in SotS and always shows a cost estimate for the author to confirm.

---

## 1. Input model: sections of 30–50 pages

The author feeds content as **sections** of roughly 30–50 manuscript pages (≈ 9,000–17,500
words at ~300–350 words per page). Sections are the working unit of Acts 0–VI (23 §5).

```python
class Section(BaseModel):
    id: str                        # sec_...
    chapter_ids: list[str]         # a section may cover one chapter or part of one
    title: str
    document_ids: list[str]        # its dictation/source files
    page_estimate: int             # words / settings.words_per_page (default 325)
    status: Literal["in_progress", "master_candidate", "master"]
```
Defaults tuned for this size (`settings.yaml`): chunk.target_tokens (muse) 12000; a budget
estimate per section is shown by `sots run --dry-run`. Sections larger than 60 pages warn and
suggest a split.

## 2. The Test Battery: Concept Cross-Analysis Tests (CCAT)

Tests are **generated, verified, then frozen**. "Verified tests" means each test is itself
proven to work before it is trusted.

### 2.1 Test families

| Family | Example tests | Kind |
|---|---|---|
| **T-TRUTH** | Every factual claim verified; 0 FALSE; every inline tier correct; every NASB quote exact | deterministic |
| **T-CONSIST** | Concept X is defined the same way wherever it appears (e.g. "Nēpsis", "the witnessing soul"); no chapter contradicts another's claim; numbers repeated across chapters are identical | deterministic + LLM entailment |
| **T-DEPEND** | No concept is used before it is introduced (reading order); every callback points backward | deterministic (concept graph) |
| **T-MESSAGE** | Each core message (M1–M7) is stated, illustrated, and evidenced in its home chapters; each chapter message lands (the Audience Lab MRR) | measured |
| **T-INTENT** | Every AIM entry's intended move lands (MGE E1 ≥ 4) | MGE |
| **T-ARC** | The intensity curve matches the architecture; the climax sits where planned; the phase labels are correct | measured + MGE |
| **T-VOICE** | Voice similarity per chapter ≥ target; protected terms intact; 0 banned clichés | deterministic |
| **T-FRAME** | `[BELIEF]` statements remain belief-framed; `[LIVE]` sources are attributed; composites disclosed | deterministic |
| **T-SAFE** | No shaming/pathologizing; crisis resources where needed; no diagnosis of real people | MGE + deterministic |
| **T-LEGAL** | Every legal issue resolved or waived with the attorney flag; the banner is in the legal appendix | deterministic |
| **T-LOAD** | The protocol load is within the book's budget (OI-29) | measured |
| **T-REPEAT** | Each motif follows its serial plan; no anchor is taught in full twice | deterministic |
| **T-CHALLENGE** | Every "revise" outcome from the last Reasoning Report (26) is addressed or explicitly declined | deterministic |
| **T-PROMISE** | Every forward promise in the text (the Promise Ledger) is fulfilled in its assigned chapter; none is unassigned | deterministic + MGE |
| **T-FORM** | Each chapter follows its form (default: the Chapter Form Template from Ch1): cold open, honest-limits section, instrument with a notebook step, bridge | deterministic + MGE |
| **T-REFERENCE** | Each chapter's voice and emotional register is graded against the reference chapter (Ch1) exemplars | MGE |
| **T-CROSS** | **Cross-analysis probes**: generated question pairs that check whether ideas in different chapters combine coherently (e.g. "Does Ch7's grace-without-earning conflict with Ch12's call to greatness?" → the text must reconcile it) | MGE-graded |

### 2.2 Generating and verifying tests (`audit/testgen.py`)
1. **Generate:** deterministic families come from the foundation + concept graph. T-CROSS
   probes come from an LLM (task `audit.probe_gen`) over every pair of core messages and every
   pair of chapters sharing a concept (with a cap).
2. **Verify each test** (a "test of the test"):
   - it must PASS on a **known-good fixture** (a passage written to satisfy it), and
   - it must FAIL on a **known-bad fixture** (a mutated passage: a flipped claim, a removed
     belief marker, a wrong NASB word, a forward reference, a changed number).
   - Tests that don't discriminate are discarded, and the discard is logged.
3. **Freeze:** the verified battery is versioned (`eval/master_battery/v<N>/`) with a hash. A
   Master Audit always runs a **frozen** battery, so results are comparable across runs.
4. **Author review:** the T-CROSS probes are shown to the author once per battery version.
   The author can mark probes as out of scope.

## 3. Running the Master Audit (`sots master-audit [--sections …|--book]`)

```
1. Preconditions: every in-scope chapter has completed Act VI (or is marked 'audit anyway')
2. Load the frozen battery vN (or build vN+1 if the foundation changed: §2.2)
3. Run all deterministic families
4. Run the MGE-graded families (profile `master_audit`)
5. Run the audience final panel on the whole book in reading order (cohort-weighted)
6. Aggregate → Master Audit Report + certification level
7. If CERTIFIED: produce the Master Version export (19 §6) stamped with the battery version
   and all scores
```

### 3.1 Certification levels
| Level | Requires |
|---|---|
| **MASTER** | 100% of critical tests pass (TRUTH, FRAME, SAFE, LEGAL, DEPEND); ≥ 95% of the others; the MGE MASTER score ≥ 95 for every chapter |
| **CANDIDATE** | Critical tests 100%; the others ≥ 85% |
| **NOT READY** | Any critical failure |

The report lists every failing test with its exact location and the fix direction. The fixes
flow back as Proposals or as revision notes (R-MGE-04). **No automatic rewriting.**

## 4. Outputs
- `data/exports/<book>/master_<date>/`: the manuscript (md + docx), endnotes, bibliography,
  fact-check appendix, legal memos, plus `MASTER_AUDIT.md` (all results) and
  `master_certificate.json` (battery version, engine versions, scores, hashes).
- A history of Master Audits, so every certification can be traced and reproduced (F18 replay).

## 5. Routing
```yaml
  audit.probe_gen:   {provider: muse, temperature: 0.3, max_output_tokens: 3000}
  audit.fixture_gen: {provider: muse, temperature: 0.2, max_output_tokens: 2000}
  audit.probe_eval:  {provider: muse, temperature: 0.0, max_output_tokens: 1500}
```
