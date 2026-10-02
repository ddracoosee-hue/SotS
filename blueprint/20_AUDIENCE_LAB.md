# 20 — AUDIENCE LAB (text mechanics panel + adult reader persona panel + learning loop)

**Purpose:** audit the regenerated text from many human perspectives, **adults only**,
centred on Gen Z adults and Millennials, with a small Gen X outside view (21 §1). Turn the
reactions into numbers, send them back to the rewriting agent, and repeat until the chapter
hits its target message for its target readers, **without sacrificing the author's voice.**

Research grounding: `21_TARGET_AUDIENCE_RESEARCH.md`. Read it before building this team.

---

## 1. Placement in the flow
- **Act III**: runs on the Pass A revision (19 §3). Loop: Lab → Audience Brief → Line Editor
  (audience edits) → Style Analyst + Cross-Checker → Lab again (≤ 3 loops).
- **Act VI**: a final check on the Pass B revision (no-regression gate, §5.3).
- **Quick pitch mode**: a cheap panel pass on proposal pitches for grader criterion U3 (§4.4).

## 2. Team roster

| Sub-team | Agent | Output |
|---|---|---|
| Text Mechanics Panel | **Phrasing Analyst** | `MechanicsFinding`s + metrics |
| | **Pacing Analyst** ("speed") | " |
| | **Tonality Analyst** | " |
| | **Context Analyst** | " |
| Persona Panel | **Persona Readers** (12 by default, from `config/personas.yaml`) | `PersonaReaction`s (3 samples each) |
| Synthesis | **Panel Aggregator** (deterministic) | `AudienceScorecard` |
| | **Audience Brief Writer** (LLM, graded G-AUD) | `AudienceBrief` for the rewriter |
| Learning | **Playbook Keeper** (deterministic + LLM summarizer) | Playbook updates, calibration (§7) |

## 3. Text Mechanics Panel

Each analyst = deterministic metrics (computed in code) + one LLM pass that *explains* the
metrics and finds the specific passages. **The metrics are never produced by the LLM (16 §4).**

| Analyst | Deterministic metrics (`audience/metrics/*.py`) | LLM looks for |
|---|---|---|
| **Phrasing** | jargon rate (a word list + rare-word frequency), cliché hits (`config/audience/cliches.txt`), "corporate words" hits, dated-slang hits (`dated_slang.txt`), therapy-speak hits (`therapy_speak.txt`: "toxic", "gaslight", "trauma response"… used loosely), hedging rate, passive-voice rate | lines that sound try-hard, condescending, or generationally off; misused clinical terms; phrasing that undercuts credibility for high-level readers |
| **Pacing** ("speed") | words per sentence (mean, stdev, rhythm variance), paragraph length distribution, estimated reading time per section (238 wpm), **hook interval** (words between hooks: questions, turns, reveals, scene changes; detected by rules + LLM confirmation), **pull-quote density** (sentences ≤ 20 words with high lexical weight), information density (named entities + numbers per 100 words), dialogue share | sagging stretches, rushed payoffs, lessons arriving before the story (violates 21 §2.6), walls of statistics |
| **Tonality** | **controlling-language index** (must/should/need to/have to/ought per 1000 words, directed at "you"), autonomy-language index (might/could/option/choose/consider), second-person ratio, exclamation rate, absolutist-word rate (always/never/everyone/nobody), warmth lexicon score | preachiness, lecturing, false cheerfulness, sarcasm that may alienate, where vulnerability builds trust vs where it overshares |
| **Context** | cultural reference inventory (from media refs + entities, with years), reference age (years since the referenced event/work), US-centric term count, assumption markers ("we all know", "obviously") | references that will date quickly; assumptions about class, culture, family structure, or faith; exclusions a diverse adult readership would notice |

```python
class MechanicsFinding(BaseModel):
    id: str; analyst: Literal["phrasing", "pacing", "tonality", "context"]
    revision_id: str; unit_ids: list[str]
    metric: str | None; value: float | None; threshold: float | None
    issue: str; suggestion: str             # a direction, not a rewrite
    severity: Severity
```

Default thresholds (`config/audience/thresholds.yaml`, editable): controlling-language
index ≤ 4 per 1000 words; hook interval ≤ 450 words; paragraph length ≤ 180 words; therapy-speak
misuse = 0 unsupported uses; absolutist rate ≤ 6 per 1000 words.

## 4. Persona Panel (adults only)

### 4.1 Persona cards (`config/personas.yaml`)
```yaml
constraints:
  min_age: 18                       # HARD RULE (validated at load): no persona under 18
  cohort_weights: {gen_z_adult: 0.60, millennial: 0.30, gen_x: 0.10}
personas:
  - id: p01
    name: "Persona 01"              # neutral ids, no stereotyped names
    cohort: gen_z_adult
    age: 22
    life_stage: "final year of university, first-generation student, works part-time"
    region: "mid-size US city"
    background_notes: "…"          # culture, family structure, faith/none, identity: written as an individual, not a category
    reading_habits: "reads nonfiction on the commute; discovers books via short video clips"
    need_for_cognition: high        # high | medium (no low: the audience is high-level thinkers)
    current_season: "anxious about the job market after graduation"
    skepticism: "distrusts influencer advice; checks sources"
    values: ["authenticity", "fairness", "independence"]
    what_would_make_them_close_the_book: "being lectured; vague claims"
```
Default panel: **12 personas**, with 7 Gen Z adults (ages 18–29), 4 Millennials (30–45), and 1
Gen X (46–61). The persona set is generated **with the author** in the TUI (the Persona Studio,
Phase P16). Muse ships a *diverse template set* for the author to edit, never a final set.

**Diversity coverage matrix** (validated at load; warnings if uncovered): region
(urban/suburban/rural, US + ≥ 2 non-US English-speaking), education path (university,
trade/vocational, self-taught), economic situation, cultural/ethnic backgrounds, faith
(religious/spiritual/none), gender identities, sexual orientations, neurodivergence,
disability, parenthood, relationship status, a veteran, an immigrant/child of immigrants,
someone in recovery, and someone currently in therapy / someone who distrusts therapy.

### 4.2 Anti-caricature rules (enforced in prompts + validators)
- **AC-01** Personas respond as thoughtful adults, in plain natural language. **No slang
  performance**, no dialect imitation, no catchphrases.
- **AC-02** Identity attributes inform *perspective*, never *voice gimmicks*. Validator: a
  banned-phrase list (`config/audience/caricature_markers.txt`, e.g. "yaaas", "oh girl",
  "no cap", "fr fr", "slay", "OK boomer") → the reaction is rejected and regenerated.
- **AC-03** Every reaction must reference **specific text** (quote ≤ 25 words + unit id).
  Generic praise or criticism is rejected.
- **AC-04** Personas may disagree with the book. Reactions that are all positive across the
  whole panel trigger a "sycophancy" warning and one re-run with a skepticism reminder.
- **AC-05** Homogeneity monitor: if the standard deviation across personas on the core
  metrics is below `min_panel_sd` (default 0.8 on a 10-point scale), flag "panel collapse"
  (research: LLM personas under-disperse, 21 §2.10). The run continues, but the metrics are
  marked low-confidence.

### 4.3 Reactions: "multiple generations of reactions"
Each persona reads each chapter section (or the whole chapter if ≤ 6000 words) **3 times**
(samples at temperature 0.8, with different random seeds / framing orders), producing:

```python
class PersonaReaction(BaseModel):
    id: str; persona_id: str; sample: int; revision_id: str; section_id: str
    first_impression: str                   # ≤ 50 words, in the persona's natural voice
    felt: list[str]                         # emotions, their words
    # Reader Journey scores (21 §3), 0–10
    recognition: float; felt_judged: float; curiosity: float; absorption: float
    insight: float; agency: float; preachiness: float
    credibility: float; intellectual_respect: float; relatability: float
    would_continue: float; would_share: float
    confusing_parts: list[QuoteRef]         # QuoteRef = {unit_id, quote ≤ 25 words, note}
    cringe_parts: list[QuoteRef]
    strongest_line: QuoteRef | None
    takeaway_in_own_words: str              # ≤ 40 words: what they think the message is
    disagreements: list[QuoteRef]
    question_for_author: str | None
```

### 4.4 Quick pitch mode
Only 4 personas (weighted to the primary cohort), 1 sample each, on the proposal pitch only.
The outputs are resonance, credibility, and relatability → grader criterion U3.

## 5. Aggregation, targets, and the feedback loop

### 5.1 AudienceScorecard (`audience/aggregate.py`, deterministic)
- Per metric: the cohort-weighted mean, per-cohort means, SD, and min/max.
- **Message Reception Rate (MRR)**: the share of reactions whose `takeaway_in_own_words`
  matches the chapter's target message. The match is judged by an entailment call
  (task `audience.takeaway_match`, temperature 0) → `{match: full|partial|none}`, where
  full = 1, partial = 0.5.
- **Journey curve**: J1–J7 scores in section order (21 §3).
- **Hotspots**: unit ids cited as confusing/cringe/disagreement by ≥ 3 distinct personas.
- **Strong lines**: unit ids cited as `strongest_line` by ≥ 3 personas (protect these in
  rewrites!).

### 5.2 Targets (`config/audience/targets.yaml`; the chapter's `reader_journey` spec overrides them)
```yaml
primary_cohort:            # gen_z_adult
  mrr: 0.80
  credibility: 7.5
  intellectual_respect: 8.0
  preachiness_max: 3.0
  felt_judged_max: 2.5
  would_continue: 7.5
all_adults:
  mrr: 0.70
  credibility: 7.0
voice_floor: 0.85          # style similarity may never drop below this for audience gains
```

### 5.3 The loop (Act III) and the no-regression check (Act VI)
```
scorecard = lab.run(revision)
while not targets_met(scorecard) and loops < 3:
    brief = brief_writer.write(scorecard, mechanics_findings)       # graded G-AUD ≥ 95
    revision' = line_editor.apply_audience_edits(revision, brief)    # hunks type audience_edit
    style + cross-check gate (19 §3.2) on revision'  → fail → discard the audience edits, stop the loop
    scorecard' = lab.run(revision')
    if scorecard' is worse than scorecard on any primary metric by > 0.3: revert, stop
    revision, scorecard = revision', scorecard'
record the final scorecard; unmet targets → a Shadow item + an author notice (not a hard block)
```
- **Voice beats audience.** An audience edit that pushes voice similarity below `voice_floor`
  is always rejected (the author's tone is non-negotiable).
- **Strong lines are protected.** Units in "strong lines" can't be edited for audience
  reasons.
- **Act VI no-regression**: the Pass B revision's primary metrics must be ≥ the Act III
  final − 0.3. Otherwise Gate B fails with the specific regressions listed.

### 5.4 AudienceBrief
```python
class AudienceBrief(BaseModel):
    id: str; revision_id: str; scorecard_id: str
    priorities: list[BriefItem]   # ≤ 8, ordered; each: {unit_ids, problem, evidence (reaction ids + metric), direction, protect: list[unit_id]}
    do_not_touch: list[str]       # strong-line unit ids
    voice_cautions: list[str]     # from the Style Guide
```

## 6. Real readers (calibration)
- `sots audience import <csv>` imports real beta-reader responses collected with the **same
  questionnaire** (a printable/online form generated by `sots audience questionnaire`), with
  optional cohort/age fields. Adults only (the importer rejects rows with age < 18).
- For each metric and cohort: `bias = synthetic_mean − real_mean`, plus the correlation across
  sections. Stored in `calibration` records.
- Calibrated scores (`synthetic − bias`) are shown next to the raw scores once a cohort has
  ≥ 5 real respondents on ≥ 2 chapters.
- If the correlation between synthetic and real (section-level) is < 0.3 for a metric, that
  metric is marked **unreliable** and removed from the automatic targets until the persona
  prompts are revised.

## 7. Learning loop: "relearn as it develops" (`src/sots/learning/`)

SotS improves between runs **without changing its rules**. It learns in four places:

| What | How | Storage |
|---|---|---|
| **Technique Playbook** | Each audience edit is tagged with the techniques it used (`config/audience/techniques.yaml`: e.g. `story_before_lesson`, `affirm_before_challenge`, `offer_not_order`, `concrete_first_step`, `callback_ending`, `verified_surprise_fact`, `author_vulnerability_first`). After re-testing, success = the targeted metric improved ≥ 0.5 with no primary regression. Keep a Beta(α, β) posterior per technique × cohort × metric. | `playbook` table |
| **Persona calibration** | §6 bias/correlation updates | `calibration` table |
| **Grader calibration** | 17 §6 health signals + author decisions | `grader_health` table |
| **Prompt evolution** | Candidate prompt versions (`*.v2.md`) are A/B-tested on the gold set + recorded runs (F18 replay). Promote one only if the eval metrics improve with no release-blocker regression. | `prompt_trials` table + `LEARNING_LOG.md` |

Rules:
- **LR-01** The learning loop **proposes**. The author approves every change to
  prompts, thresholds, rubric weights, and persona cards (a TUI "Learning" inbox).
  Playbook posteriors update automatically, because they are data.
- **LR-02** Playbook suggestions to the Brief Writer include only techniques with ≥ 10
  trials and a posterior mean success of ≥ 0.6.
- **LR-03** Every learned change is versioned and can be rolled back
  (`sots learning rollback <change_id>`).
- **LR-04** Learning never touches `01_RULES.md` behaviours, hard checks, gate thresholds for
  truth/citations, or the adults-only constraint.
- **LR-05** `LEARNING_LOG.md` gets one line per applied change: date, what, why, the evidence
  (metric deltas).

## 8. Routing additions
```yaml
  audience.mechanics_explain: {provider: local, temperature: 0.2, max_output_tokens: 2000}
  audience.persona_read:      {provider: muse,  temperature: 0.8, max_output_tokens: 1500}
  audience.takeaway_match:    {provider: local, temperature: 0.0, max_output_tokens: 200}
  audience.brief:             {provider: muse,  temperature: 0.2, max_output_tokens: 2500}
  learning.summarize:         {provider: local, temperature: 0.0, max_output_tokens: 1000}
```

**Cost note:** 12 personas × 3 samples × sections is the most expensive loop in SotS. The dry
run (04 §6) must show its estimate separately, and settings allow `samples_per_persona: 1`
for drafts.

## 9. Foundation-specific additions (23)
- **Journey spec seeds** per chapter come from the brief blocks: Block 1 → J1 Recognition;
  Block 2 → J3 Curiosity + J5 Insight; Block 3 → J5; Block 4 → J4 Transportation; Block 5 →
  J6 Agency; Block 6 → J7 Integration. J2 Safety is measured across all blocks. The author
  confirms the targets (OI-17).
- **Protocol Load Auditor** (new agent): computes each protocol's weekly time/effort cost,
  the cumulative load in reading order, and the number of simultaneously "active" practices;
  compares them against `book.protocol_budget` (OI-29). Overload → a Shadow `self_contradiction`
  item + a Proposal. Personas answer an extra question per chapter: "Which ONE practice would
  you actually try this week?" This measures the practice uptake rate.
- **Faith-passage reactance** (SC-02): personas of faith and of no faith rate
  invited-vs-recruited on faith passages; the target is preachiness ≤ 3 for both groups.
- **Tone hotspots pre-flagged from the briefs**: ch04 ("parasites", "completely broken"),
  ch03 ("You are not human!"), ch07 (the "trade it for Christ's easy yoke" prompt). The panel
  measures them first.
