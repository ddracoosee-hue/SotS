# 10 — SHADOW SELF (Stage 9)

The Shadow Self is the honest inner critic: the voice that asks what the author might
rather not hear. It has three jobs:
1. **Reflect**: find contradictions, avoidances, and self-serving framing in the text.
2. **Grade**: score the text against fixed rubrics with measurable targets.
3. **Audit the system**: grade SotS itself against its own quality goals.

All Shadow output follows R-PSY-01 to R-PSY-03: it is about the text, it is evidenced, and it
is phrased as questions.

## 1. Reflect (`shadow/reflect.py`, task `shadow.reflect`)

Input: the root + level-1 summaries, the synthesis, the top psyche findings, the fact
verdicts that are FALSE/MISLEADING/PARTIALLY_TRUE, media checks that are not
`supported_reading`, the drift report, the profile (values, self-reported biases), and the
**previous shadow reports for the same chapter** (so it notices patterns that persist).

It produces `ShadowItem`s (`03 §7`) in these categories only:

| Category | What it looks for | Example question to the author |
|---|---|---|
| `contradiction` | Two units (possibly in different documents or chapters) that conflict | "In unit 12 you say you've forgiven them; in unit 88 the anger is present-tense. Which is true now?" |
| `avoidance` | A topic the brief or profile says matters, but the text circles without landing | "The brief promises to talk about your role in the breakup. Where is it?" |
| `self_serving_frame` | The author is always the one acted upon, never the actor | "Is there a version of this story where you made a choice?" |
| `unearned_lesson` | A lesson with no story or evidence behind it (also TR-04) | "What happened to you that taught this?" |
| `harshness_asymmetry` | Others judged by a standard the author isn't held to | "Would you accept this reading if someone wrote it about you?" |
| `fact_risk` | An important argument leans on a weak or false fact | "If this statistic falls, does the chapter's argument still stand?" |
| `overreach` | A personal experience generalized to everyone | "Is this true for your reader, or true for you?" |

Code checks: every item has ≥ 1 valid unit id and a non-empty question. At most 15 items per
report, ranked by severity. If the author has marked an item as "addressed" in the TUI, and
the cited units no longer exist or have changed, a later run doesn't repeat it.

## 2. Grade (`shadow/rubric.py`, task `shadow.grade` + deterministic metrics)

### 2.1 Writing rubric (`config/rubrics.yaml`)

Each criterion is scored 1–5. **Where a metric exists, the score comes from the metric by
fixed bands, not from the LLM.** The LLM scores only the criteria marked `judged`, using the
anchors below, and must cite units.

```yaml
criteria:
  - id: factual_integrity
    weight: 0.20
    metric: share of checkable units with final_verdict in [true, mostly_true]
    bands: {5: ">=0.95", 4: ">=0.85", 3: ">=0.70", 2: ">=0.50", 1: "<0.50"}
    target: 0.90
    hard_goal: "0 FALSE verdicts left unaddressed"
  - id: evidence_quality
    weight: 0.10
    metric: mean best-supporting tier across verified units (lower is better)
    bands: {5: "<=1.5", 4: "<=2.0", 3: "<=2.5", 2: "<=3.5", 1: ">3.5"}
    target: 2.0
  - id: media_fidelity
    weight: 0.10
    metric: share of media points accurate or partly_accurate
    bands: {5: ">=0.95", 4: ">=0.85", 3: ">=0.70", 2: ">=0.50", 1: "<0.50"}
    target: 0.90
  - id: message_clarity
    weight: 0.15
    metric: share of chapter messages stated AND illustrated
    bands: {5: "==1.0", 4: ">=0.8", 3: ">=0.6", 2: ">=0.4", 1: "<0.4"}
    target: 1.0
  - id: on_track
    weight: 0.10
    metric: 1 - unmapped_ratio
    bands: {5: ">=0.85", 4: ">=0.75", 3: ">=0.60", 2: ">=0.45", 1: "<0.45"}
    target: 0.80
  - id: voice_consistency
    weight: 0.10
    metric: voice similarity
    bands: {5: ">=0.85", 4: ">=0.75", 3: ">=0.65", 2: ">=0.50", 1: "<0.50"}
    target: 0.80
  - id: honesty_accountability
    weight: 0.10
    judged: true
    anchors:
      5: "Author owns their choices and mistakes; others are portrayed fairly"
      3: "Some self-examination; some one-sided portrayal"
      1: "Author is consistently only acted upon; others are villains"
  - id: reader_utility
    weight: 0.10
    judged: true
    anchors:
      5: "Every lesson is concrete and actionable, grounded in a story"
      3: "Some lessons actionable; some vague or preachy"
      1: "Lessons are abstract or absent"
  - id: emotional_truth
    weight: 0.05
    judged: true
    anchors:
      5: "Emotion is specific, earned, and matches events"
      3: "Emotion is present but generic or uneven"
      1: "Emotion is absent, performative, or mismatched"
```

- `overall` = the weighted mean.
- `met` = the measured value reaches the target (for judged criteria: score ≥ 4).
- `goals_met / goals_total` is shown prominently.
- The author may edit the weights, bands, and targets. The code reads them; nothing is
  hard-coded.

### 2.2 Goals and trend (`shadow/goals.py`)
- Keep the history of every `ShadowReport` per chapter_id.
- `trend_vs_previous` = the score delta per criterion vs the latest previous run on the
  same chapter.
- The **Goals** screen shows each criterion: current → target, a sparkline across runs, and
  ✔/✘.
- The **hard goals** (e.g. no unaddressed FALSE verdicts) block the "chapter ready" status
  in the TUI until they are met, or until the author explicitly waives them. A waiver is
  stored with a reason.

## 3. System audit (`shadow/system_audit.py`)

The Shadow also grades **SotS itself**, using `config/system_goals.yaml` and the eval
harness (`14_TESTING_AND_EVAL.md`):

```yaml
goals:
  unit_extraction_coverage:     {target: ">=0.95", how: "share of gold claims matched by an extracted unit"}
  classification_accuracy:      {target: ">=0.85", how: "content_type accuracy on the gold set"}
  claim_kind_accuracy:          {target: ">=0.80"}
  fabricated_citation_rate:     {target: "==0",    how: "evidence whose excerpt is not in the cached page text"}
  verdict_agreement_with_gold:  {target: ">=0.80", how: "exact or adjacent verdict vs the human label"}
  false_true_rate:              {target: "<=0.02", how: "gold FALSE claims that the system called TRUE/MOSTLY_TRUE"}
  verdict_stability:            {target: ">=0.90", how: "same final verdict across 2 runs with cache disabled"}
  offset_integrity:             {target: "==1.0",  how: "every unit's text == document[start:end]"}
  engine_citation_validity:     {target: "==1.0",  how: "every finding cites existing unit ids"}
  cost_per_10k_words:           {target: "author sets"}
  minutes_per_10k_words:        {target: "author sets"}
```
- `sots audit` runs the eval harness, computes each goal, and writes
  `data/runs/audit_<date>.md`.
- Any goal at `==0` or `==1.0` that fails is a **release blocker**. It shows in red in the
  TUI, and Muse must fix it before the next build phase is considered done.
