# 17 — QUALITY GATE GRADER

> **Superseded in part by `27_MASTER_GRADING_ENGINE.md`:** this file defines the gate
> mechanics (thresholds, the loop, anti-gaming, calibration). The judging itself (Factual +
> Emotional sections, the Professional Perspective Panel, stability) is the MGE. Rubrics here
> become MGE *profiles*. The regeneration loop is internal quality control only. The author never
> gets rerolls (R-MGE-04).

**Purpose:** nothing reaches the author for review until it scores **≥ 95 / 100** on a
detailed rubric for **reliability** (can it be trusted?) and **usability** (does it work in
this book, in this place, for this reader?). Below that bar, the producing agent must
regenerate. Items that never clear the bar are archived, not shown.

---

## 1. Where the gate applies (`config/grader.yaml → gates`)

| Gate | Artifact | Rubric | Required |
|---|---|---|---|
| G-PROP | Proposals to the author (18) | `proposal` | yes |
| G-REPORT | Deep research reports (11) | `research_report` | yes |
| G-HUNK-B | Pass B rewrite hunks shown to the author (19 §4) | `rewrite_hunk` | yes |
| G-HUNK-A | Pass A rewrite hunks | `rewrite_hunk` | only if `rewrite.pass_a.author_review: true` |
| G-LEGAL | Legal position & defense memos (22) | `legal_memo` | yes |
| G-AUD | Audience briefs sent to the rewriter (20) | `audience_brief` | yes |

## 2. The score

```
score = 100 × Σ (weight_c × criterion_score_c / 5)        # each criterion 0–5, weights sum to 1
PASS  ⇔ score ≥ threshold (default 95)
        AND every criterion ≥ its floor (default 4 of 5)
        AND every hard check passes
```
- **Hard checks** are deterministic and binary. If one fails, the score is 0 and the item is
  regenerated with that reason.
- **Measured criteria** are computed by code from data (tiers, verdicts, similarity
  scores…).
- **Judged criteria** are scored by LLM graders against the written anchors.

Practically, with the floor at 4: each criterion scored 4 instead of 5 costs `20 × weight`
points, so the criteria sitting at 4 may add up to **at most 25% of the total weight**.
Everything else must be a 5. That is intentionally strict.

## 3. Rubrics (`config/grader.yaml → rubrics`)

### 3.1 `proposal` (the main rubric)

**Hard checks**
- H1 Every factual statement links to verified `Evidence` (R-TRUTH-02).
- H2 No evidence item has final verdict FALSE / MISLEADING, unless the proposal *is* a
  correction or counterpoint that says so.
- H3 At least 2 placement options, each pointing at an existing unit id or a named
  new-section anchor.
- H4 It links to ≥ 1 core message or chapter brief (R-EXP-07).
- H5 No open HIGH legal flag from the pre-screen (22 §2).
- H6 Quoted material ≤ the fair-use excerpt limits (07 §2: ≤ 300 characters; lyrics are
  never quoted).

**Reliability (weight 0.50)**

| ID | Criterion | Type | 5 = | 3 = | 1 = |
|---|---|---|---|---|---|
| R1 | Source strength | measured | best source tier 1–2, ≥ 2 independent domains | tier 3 only | tier 4–5 only |
| R2 | Verification status | measured | all key claims TRUE/MOSTLY_TRUE | some PARTIALLY_TRUE | UNSUPPORTED present |
| R3 | Claim–evidence fit | judged | evidence states exactly what the proposal says | nearby but broader or narrower | inferred leap |
| R4 | Recency / currency | measured | data ≤ 5 years old, or timeless | 5–10 years | > 10 years presented as current |
| R5 | Balance | judged | counter-evidence acknowledged | mentioned lightly | one-sided |

Weights within reliability: R1 .12, R2 .14, R3 .12, R4 .05, R5 .07.

**Usability (weight 0.50)**

| ID | Criterion | Type | 5 = | 3 = | 1 = |
|---|---|---|---|---|---|
| U1 | Message relevance | measured (ledger similarity) + judged | directly advances a priority-1 message | tangential | unrelated |
| U2 | Placement fit | judged | slots in naturally after the cited unit | needs bridging | disrupts flow |
| U3 | Audience fit | measured (a quick panel pass on the pitch, 20 §4.4) | predicted resonance ≥ 8/10 in the primary cohort | 6–7 | < 6 |
| U4 | Voice compatibility | measured (style distance of the pitch excerpt) | fits the style guide | needs adaptation | clashes |
| U5 | Novelty | measured | adds something not already in the manuscript | partly redundant | duplicate |
| U6 | Integration effort vs value | judged | high value, low effort | balanced | low value, high effort |
| U7 | Legal/ethical cleanliness | measured (pre-screen) | no flags | LOW flags only | MEDIUM flags |

Weights within usability: U1 .12, U2 .08, U3 .08, U4 .06, U5 .06, U6 .05, U7 .05.

### 3.2 `rewrite_hunk`
Hard checks: the meaning-preservation check passes (19 §5.3); the cross-check passes; protected
terms are intact; the edit budget is respected.
Criteria: voice fidelity (measured, .30), clarity gain (judged, .20), correctness (measured:
LanguageTool issues resolved, .15), audience metric delta (measured, .15), flow (judged, .10),
necessity ("was this change needed?", judged, .10).

### 3.3 `research_report`
Hard checks: R-EXP-03 validator passes; counter-perspectives are non-empty.
Criteria: source diversity (measured, .15), tier-1/2 share (measured, .20), sub-question
coverage (measured, .20), synthesis quality (judged, .15), connection to the author's text
(judged, .15), clarity (judged, .15).

### 3.4 `legal_memo`
Hard checks: every legal authority cited was fetched and excerpt-verified; endorsement ≥ 6/8;
no unresolved HIGH risk.
Criteria: authority quality (measured: primary law / official guidance share, .25),
issue coverage (measured, .20), argument coherence (judged, .20), dissent addressed (judged,
.15), practicality of the edits (judged, .20).

### 3.5 `audience_brief`
Hard checks: every claim about reader reactions references persona reaction ids; the metrics
match the aggregator output exactly.
Criteria: actionability (judged, .35), prioritization (judged, .25), voice-safety (does it ask
for changes that would violate the style guide? judged, .20), evidence-backing (measured, .20).

## 4. Grading procedure (`src/sots/grader/`)

1. Run the **hard checks** (deterministic). On failure → return score 0 + reasons.
2. Compute the **measured** criteria.
3. Run **two independent judge graders** for the judged criteria:
   - Grader A: prompt `grader/judge_strict.v1.md` (skeptical editor persona)
   - Grader B: prompt `grader/judge_reader.v1.md` (target-reader advocate persona)
   - Both are on temperature 0, and if possible on different models/providers
     (routing `grader.judge_a`, `grader.judge_b`).
   - For each judged criterion, take the **lower** of the two scores.
   - If the two differ by ≥ 2 points on any criterion → call Grader C
     (`grader/judge_tiebreak.v1.md`) for that criterion and take the median of A, B, C.
4. Compute the weighted score. Store a `GradeRecord`.

```python
class CriterionResult(BaseModel):
    id: str; type: Literal["hard", "measured", "judged"]
    score: float                     # 0–5 (hard: 0 or 5)
    floor: float
    evidence: str                    # why: numbers or quoted anchor + cited ids
    judges: dict[str, float] = {}    # judge_a / judge_b / judge_c

class GradeRecord(BaseModel):
    id: str; artifact_type: str; artifact_id: str; attempt: int
    rubric_id: str; rubric_version: int
    criteria: list[CriterionResult]
    score: float                     # 0–100
    passed: bool
    feedback_for_generator: list[str]  # concrete, actionable, ≤ 8 items
    created_at: datetime
```

## 5. Regeneration loop

```
attempt = 1
loop:
    artifact = producer.generate(inputs, feedback)
    grade    = grader.grade(artifact)
    if grade.passed: submit to the author queue; stop
    if attempt == max_attempts (default 4): archive as BELOW_BAR; stop
    if attempt ≥ 3 and grade.score − previous_score < 1.0: archive as PLATEAU; stop
    feedback = grade.feedback_for_generator (+ failing hard checks)
    attempt += 1
```

### 5.1 Anti-gaming rules
- **GR-01** The generator never sees the grader's prompts, rubric anchors, or numeric
  scores. It only sees `feedback_for_generator`, which is phrased as edits to make.
- **GR-02** Graders never see the attempt number or earlier scores (no "it improved, so
  pass it").
- **GR-03** Graders cannot change measured criteria or hard checks. Only code computes those.
- **GR-04** The feedback must be concrete ("Replace the 2014 figure with a source from
  2019+, or label it as dated"). Vague feedback ("make it better") is rejected by a validator,
  and the grader is re-run.
- **GR-05** A producer is not allowed to lower the ambition of an artifact just to pass
  (e.g. removing all facts to dodge H1). The novelty and relevance criteria guard against this.
  A drop of more than 30% in content length between attempts triggers a reviewer flag.

## 6. Calibration and health (`grader/calibration.py`)

- The author's decisions on submitted items (accept / modify / reject + reason) are stored.
  They are the ground truth for **usability**.
- Health signals (computed weekly or per 50 grades, shown in the TUI):
  - **Too lenient**: > 60% of items pass on the first attempt, *and* the author rejects
    > 30% of passed items.
  - **Too strict**: < 5% of items pass within max_attempts over the last 50.
  - **Judge disagreement**: the tiebreak rate is > 25%.
  - **Rejection reasons cluster**: the top 3 author rejection reasons for passed items; these
    suggest missing criteria.
- A health alert creates a proposal for the author to adjust the rubric (weights, anchors,
  threshold). **Rubric changes are never automatic** (see the learning rules in 20 §7).
- A calibration set of 20 hand-graded items (`eval/grader_gold/`) is used in `sots eval`.
  Target: judge agreement with the human grade within ±1 point on ≥ 80% of the criteria.

## 7. Below-bar archive
- Items stored with all their attempts and grades, viewable in the TUI ("Didn't make the
  cut").
- The author may manually promote an item. That is logged as an override, and counts as a
  "too strict" signal.
