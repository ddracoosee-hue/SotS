# 27 — MASTER GRADING ENGINE (MGE)

**Author directive (2026-09-28):** "I don't want a system that constantly regenerates different
responses depending on what the user asks to regenerate. I want an engine dedicated to having a
factual and emotional grading section that the team of agents relies on religiously, so the
presented response is master-tested and reviewed against professional writing and self-help
book author perspectives."

The MGE is the **single source of judgment** in SotS. `17_QUALITY_GATE_GRADER.md` defines the
gate *mechanics* (thresholds, hard checks, the regeneration loop, calibration). This document
defines the *engine* those gates call: its two grading sections, its professional panel, and
its stability guarantees. Where 17 and 27 differ, 27 wins.

---

## 1. The contract

- **R-MGE-01 One judge.** No agent grades its own output, and no team keeps a private rubric.
  Every judgment of quality, truth, voice, or emotional effect goes through the MGE.
- **R-MGE-02 The verdict is binding.** An output the MGE fails cannot be shown to the author,
  written into a revision, or passed to the next act. There is no bypass flag. (The author's
  explicit waiver, R-GATE-03, is recorded as a waiver, not as a pass.)
- **R-MGE-03 Stable judgment.** Same artifact + same engine version = same grade.
  Temperature 0, fixed rubric versions, cached judge calls, and a stability test (§6).
- **R-MGE-04 One master answer, not rerolls.** SotS never offers "regenerate" as a reroll of
  the same request. For any input state it produces **one** master-tested output. If the
  author wants something different, they give a **revision note**. The note becomes a new,
  recorded input and runs through the full pipeline and the MGE. Asking again with no new
  input returns the same cached master output. (The only designed multi-option outputs are
  proposal placement/mode options, 18 §2, and they are graded as a set.)

## 2. Section F: Factual Grading

Scores whether content is **true, correctly sourced, and honestly labelled**. It is almost
entirely measured, not judged.

| ID | Criterion | How it is computed |
|---|---|---|
| F1 | Claim verification | Share of checkable claims with final verdict TRUE/MOSTLY_TRUE; FALSE = hard fail unless it is presented as a correction |
| F2 | Source strength | Best supporting tier + independence (06 §7) |
| F3 | Citation integrity | Excerpt-verified evidence for every factual sentence (R-TRUTH-02); 100% required |
| F4 | Epistemic tier correctness | Inline and endnote tiers equal the computed tier (25 §2) |
| F5 | Attribution correctness | Quotes, names, dates, and works match their sources; author markers are honoured (25 §7) |
| F6 | Evidence-grade honesty | Protocol grades match the audit (25 §4) |
| F7 | Scripture accuracy | NASB text/reference match; term glosses supported or flagged (25 §5) |
| F8 | Belief/source framing | `[BELIEF]` stays belief-framed; `[LIVE]` sources are attributed (25 §7) |
| F9 | Consistency | No contradiction with verified anchors or other chapters (Master Audit cross-tests, 28) |

Section score F = weighted mean (weights in `config/mge.yaml`). **F1, F3, F7-quotes, and F8
are hard checks.**

## 3. Section E: Emotional Grading

Scores whether content produces the **psychological and emotional effect the author intends**,
for the adult target reader, **without manipulation**. It is measured where possible and judged
against anchors elsewhere.

| ID | Criterion | Source of the score |
|---|---|---|
| E1 | Intent fidelity | Match to the **Author Intent Model** (26 §2): does the passage make the psychological move the author intends here? (judged by the panel, anchored to the AIM entry) |
| E2 | Reader Journey hit | Audience Lab J1–J7 scores vs the chapter's journey spec (20, 21 §3) (measured) |
| E3 | Emotional truth | Specific, earned emotion that matches the events; no performativity (judged) |
| E4 | Safety | J2 safety + felt_judged + no shaming/pathologizing (measured + judged); **floor 4/5** |
| E5 | Reactance | Controlling-language index, preachiness (measured) |
| E6 | Voice | VOICE(t) from the Voice Model (29 §3.5), with its weight scaled by corpus confidence (29 §3.6) (measured) |
| E7 | Resonance | Primary cohort relatability, credibility, intellectual respect (measured, calibrated per 20 §6) |
| E8 | Ethical persuasion | No false urgency, fear-mongering, or dark patterns (judged; any violation → hard fail) |

Section score E = weighted mean. **E4 floor and E8 are hard checks.**

## 4. Section P: the Professional Perspective Panel

Every judged criterion (in F or E) is scored by a fixed panel of **professional perspectives**.
Each is a judge persona with its own anchored checklist (`prompts/mge/panel/*.v1.md`):

| Seat | Perspective | Looks for |
|---|---|---|
| P1 | **Developmental editor** | Structure, argument flow, chapter purpose, pacing |
| P2 | **Line editor** | Sentence-level clarity, rhythm, precision, clichés |
| P3 | **Acquisitions editor / literary agent** | Market readiness, hook strength, differentiation, promise delivered |
| P4 | **Bestselling self-help author** | Actionability, reader transformation, earned authority, story-to-lesson craft |
| P5 | **Clinical psychologist reviewer** | Accuracy of psychological claims, safety for vulnerable readers, no pseudo-diagnosis |
| P6 | **Research-methods reviewer** | Evidence use, overclaiming, causal language, hedging |
| P7 | **Sensitivity & ethics reader** | Fairness to real people and groups, dignity, stereotype risk |
| P8 | **Theology-literate reader** | Scripture handling, exegetical care, respect across traditions (faith passages only) |
| P9 | **Target adult reader** | "Would I keep reading? Do I feel respected?" |

Rules:
- The seats that apply to a criterion are defined in `config/mge.yaml` (e.g. E1 uses P1, P4,
  P5, P9; F4 is measured, so no panel).
- **Aggregation:** the median seat score per criterion, but **any seat scoring ≤ 2 with a cited
  reason triggers a blocking note**. The artifact can pass only if the producer addresses the
  note, or if a second, independent run of that seat does not reproduce the concern.
- The panel personas describe professional *standards*. They never impersonate real,
  named people.
- **Calibration library** (`eval/mge_calibration/`): author-approved exemplar passages at
  score levels 2/3/4/5 for each judged criterion. They are drawn from the author's own
  accepted text and from **short public-domain or properly licensed** excerpts, never large
  copyrighted passages. Judges see the exemplars as anchors.

## 5. The master score

```
MASTER = 100 × (wF × F + wE × E) / 5      # default wF = 0.5, wE = 0.5
PASS ⇔ MASTER ≥ 95  AND all hard checks pass  AND every criterion ≥ its floor
       AND no unresolved blocking note from the panel
```
Each artifact type (proposal, block draft, rewrite hunk, legal memo, audience brief, research
report, reasoning report, challenge) maps its specific criteria onto F and E in
`config/mge.yaml`. Rubric ids in 17 §3 become **profiles** of the MGE.

## 6. Stability and trust

- **Stability test** (`sots mge stability`, and a weekly check): re-grade 20 cached artifacts
  with the cache disabled. The MASTER score must be within ±2 and the pass/fail identical in
  ≥ 95% of cases. Failure → an MGE health alert; the affected rubric version is frozen until
  it is fixed.
- **Versioning:** every rubric, panel prompt, and exemplar set is versioned. A GradeRecord
  stores the MGE version. Changing the MGE requires the author's approval via the Learning
  Inbox (LR-01) plus a passing replay test on the calibration library.
- **Transparency:** every grade shows its section scores, per-criterion evidence, panel seat
  notes, and the exact reason for failure, in the TUI (Grade Inspector).
- **No self-referential leakage:** producers never see panel prompts or exemplars (GR-01).

## 7. How agents "rely on it religiously"

- The `BaseAgent` lifecycle (16 §2) calls the MGE for every card with a rubric. Cards without
  a rubric may not produce author-facing or text-changing output (doctor check).
- Reasoning and challenge teams (26) use the MGE to decide which arguments are strong. They
  never decide by themselves.
- The Master Audit (28) uses MGE profiles as its scoring backbone.

## 8. Config and routing
`config/mge.yaml`: sections, criteria, weights, floors, hard checks, panel seats per criterion,
profiles per artifact type, and exemplar set versions.
```yaml
  mge.panel_seat:   {provider: muse, temperature: 0.0, max_output_tokens: 1200}   # one call per seat
  mge.blocking_recheck: {provider: muse, temperature: 0.0, max_output_tokens: 800}
```
