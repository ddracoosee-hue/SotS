# 29 — VOICE LAB (the author's writing-style model)

**Author directive (2026-09-29):** "Expand upon the format of my personal writing to be more
connected to my personal writing style. I want to add a section where I can add more
data/text that affects a complex algorithm of my writing style and prose, and all minor aspects
of an assessment to be scaled based off the information provided."

The Voice Lab is where the author **feeds writing in**. From it SotS builds a
**multi-dimensional, confidence-weighted Voice Model**. The model then drives every voice-related
decision and every voice-related assessment in the system. The more the author feeds it, the
sharper and stricter it becomes, and every assessment scales with that.

It **supersedes** `09 §5` (voice fingerprint) and `19 §1.2` (the Style Guide is now *derived*
from the Voice Model). Where they conflict, 29 wins.

---

## 1. The intake section: `profile/voice_corpus/`

A dedicated folder the author can keep adding to, at any time, in any amount.

```
profile/voice_corpus/
├── README.md                  # how to add material (plain instructions for the author)
├── manifest.yaml              # one entry per item (auto-created on intake; the author may edit)
├── final/                     # polished prose the author signs off on (e.g. Ch1)   → register: final
├── drafts/                    # the author's own drafts                              → register: draft
├── spoken/                    # dictation / voice-memo transcripts, word vomits      → register: spoken
├── casual/                    # texts, posts, journal entries, emails                → register: casual
├── pairs/                     # RAW → FINAL pairs: the dictation + the finished version of the same passage
└── not_me/                    # counter-examples: text the author says does NOT sound like him (AI drafts he rejected, etc.)
```

Intake: `sots voice add <file|folder> --register final|draft|spoken|casual [--weight 0.5-2.0] [--note "…"]`,
or drop files in a folder and run `sots voice sync`. The TUI Voice Lab screen offers the same.
Ch1 (`profile/manuscript/ch01_the_modern_day.md`) is registered automatically as `final`, with weight 2.0.

```python
class VoiceSample(BaseModel):
    id: str; path: str; sha256: str
    register: Literal["final", "draft", "spoken", "casual", "pair_raw", "pair_final", "not_me"]
    written_on: date | None
    words: int
    weight: float = 1.0            # the author's trust weight (0.5–2.0)
    recency_weight: float          # computed (§3.3)
    note: str | None
    added_at: datetime
```

**Register separation.** Spoken and casual samples teach *what the author thinks and how he
talks*. Final samples teach *how he writes for readers*. They are modelled separately, so a
word vomit never drags the prose model toward the casual register. The **pairs** teach the
transformation between them (§4).

## 2. The Voice Model: features

The model is a vector of **features** in 10 families. Every feature is computed per sample, then
aggregated per register. Everything is measured by code (stdlib + rapidfuzz, no new
dependencies), except the features marked *(LLM-annotated)*. Those are extracted by a
temperature-0 annotation pass with a fixed schema and cached per sample.

| Family | Example features (not exhaustive; Muse implements ≥ 120 features in total) |
|---|---|
| **F-LEX: Lexical** | type-token ratio (standardized per 1,000 words); average word length; share of Anglo-Saxon vs Latinate words (via a suffix heuristic + word list); contraction rate; "somebody" vs "someone" preference; intensifier rate; hedge-word rate; profanity rate; signature words (log-odds vs a general-English reference list) |
| **F-SYN: Syntax** | sentence length mean/SD/skew; clause count per sentence (punctuation + conjunction heuristic); sentence-initial conjunction rate ("And", "But", "So"); question rate; fragment rate; passive rate; parenthetical rate; list-of-three rate |
| **F-RHY: Rhythm** | long→short alternation index (how often a ≥ 25-word sentence is followed by a ≤ 8-word sentence); paragraph length distribution; paragraph-final short-sentence rate ("That's what a structure does."); cadence repetition (anaphora) rate |
| **F-PUN: Punctuation** | per-1,000-word rates for , ; : — – … ( ) " ' ! ?; em-dash spacing style; serial comma usage |
| **F-NUM: Numbers & evidence** | numbers written out vs as numerals; study-mention pattern (name + year + sample + caveat); the share of evidence sentences followed within 2 sentences by a caveat |
| **F-EPI: Epistemic moves** *(LLM-annotated + patterns)* | the rate and form of prose tier signals (DF/PT/IE/HEDGE/BELIEF, 25 §3); self-correction moves ("first draft", "I have to reverse"); objection-steelman moves; "I'm not going to pretend" honesty markers |
| **F-RHE: Rhetorical moves** *(LLM-annotated)* | naming a phenomenon ("I call this…"); reframing ("That isn't X. It's Y."); refrains ("…isn't a character flaw"); "Hold onto that pattern" signposting; direct reader challenges; the "Read that as a set of instructions" turn |
| **F-DIS: Discourse & structure** | scene-first openings; concrete→mechanism→evidence→meaning sequencing per section; roadmap paragraphs; section-closing lines; bridge endings |
| **F-EMO: Emotional register** *(LLM-annotated)* | warmth, vulnerability, authority, and irony levels; the "scar, not open wound" disclosure style; crisis-note pattern; humor frequency and type |
| **F-PER: Person & address** | first/second/third-person shares; "you" density by section type (hooks and instruments high, evidence low); "we" as generational inclusion |

Each family also contains **negative features**, learned from `not_me/` and the banned list:
AI-cliché rate, corporate-word rate, preamble patterns, bracket tags (the author uses prose
signals), and em-dash overuse.

## 3. The "complex algorithm": how features are weighted and scaled

For every feature *f* in register *r*:

### 3.1 Author value
`μ_f` = the weighted mean over samples (weight = the author's trust weight × recency_weight ×
the square root of the words, so long texts count more, but with diminishing returns). `σ_f` = the
weighted standard deviation across samples.

### 3.2 Importance: which features actually define the voice
```
consistency_f      = 1 / (1 + CV_f)                 # CV = σ_f / |μ_f|: stable features matter more
distinctiveness_f  = |μ_f − ref_f| / ref_sd_f       # distance from the general-English reference profile, capped at 3
contrast_f         = |μ_f − notme_f| / pooled_sd    # separation from 'not_me' samples (0 if none)
confidence_f       = n_eff_f / (n_eff_f + k)        # n_eff = effective sample count; k = 5 (the prior strength)

importance_f = confidence_f × (0.45·consistency_f + 0.35·min(distinctiveness_f,3)/3 + 0.20·min(contrast_f,3)/3)
```
The reference profile (`ref_f`, `ref_sd_f`) comes from a bundled, license-clean general-English
sample set (public-domain essays + generated neutral prose). It is stored with its version.

### 3.3 Recency
`recency_weight = 0.5 ^ (age_in_months / half_life)`, with `half_life` = 18 months by default.
The author's voice evolves. Recent writing counts more, but old writing is never discarded.
`final` samples get a floor of 0.6.

### 3.4 Shrinkage (small data stays humble)
With little data, each feature estimate is pulled toward a broad prior:
`μ̂_f = confidence_f·μ_f + (1 − confidence_f)·prior_f`.
The prior for a newly added register is the author's other registers (mapped through the
transformation model, §4), or the reference profile if there is nothing else.

### 3.5 Voice similarity (replaces 09 §5.2)
For a candidate text *t* in register *r*:
```
z_f(t)      = (x_f(t) − μ̂_f) / max(σ_f, floor_f)
fit_f(t)    = exp(−½ z_f(t)²)                           # 1 = exactly on-voice
numeric_sim = Σ importance_f · fit_f(t) / Σ importance_f
negative_pen= Σ over negative features of max(0, x_f(t) − tolerance_f) · w_neg
llm_sim     = the MGE panel seats P2 + P9 judging against the voice exemplars (27 §4)
VOICE(t)    = clamp(0,1, 0.7·numeric_sim + 0.3·llm_sim − negative_pen)
```
The weights `0.7 / 0.3` shift toward the numeric side as the corpus grows:
`w_num = 0.5 + 0.3·corpus_confidence`, where
`corpus_confidence = total_final_words / (total_final_words + 20,000)`.

### 3.6 Scaling every assessment to the information provided
The author asked for **all minor aspects of an assessment to be scaled** to the amount and kind
of material provided. Concretely:

| Assessment | How it scales |
|---|---|
| **Voice thresholds** (Gate A 0.85, Gate B 0.88, the audience voice floor 0.85) | `threshold_eff = base − 0.10·(1 − corpus_confidence)`. They start lenient with little data and reach the full strictness as the corpus grows. They never exceed base + 0.03. |
| **Per-feature tolerance** | `tolerance_f = 1.5·σ_f / confidence_f`. Uncertain features are tolerated more, and features the author is very consistent on are enforced tightly. |
| **Which features the Style Analyst reports** | Only features with importance ≥ 0.25. The rest are shown as "not yet characteristic". |
| **MGE E6 (voice) weight** | Scales from 0.5× to 1.0× of its configured weight by corpus_confidence. |
| **Block Synthesis author-proportion floor (R-SYN-07)** | +0.05 when the pair-trained transformation model confidence ≥ 0.7 (more of the draft can safely stay in the author's own words). |
| **Protected-term discovery** | Terms become protected automatically (after a notice to the author) when they appear in ≥ 2 final samples with log-odds ≥ 3 vs the reference. |
| **Assessment confidence labels** | Every voice verdict carries a confidence label: Low (< 0.4), Medium, High (≥ 0.75). Low-confidence voice failures are warnings, never hard blocks. |

## 4. The Transformation Model (spoken/draft → final)

Learned from `pairs/`: the author's raw dictation for a passage + his finished version of it.
Ch1's raw dictation, if the author has it, is the most valuable pair SotS could receive (OI-40).
- **Feature deltas:** per feature, the average change from raw to final (e.g. sentence length +6,
  fragments −40%, prose tier signals added, profanity removed or kept).
- **Move library:** LLM-annotated alignments (rapidfuzz sentence alignment, then classified): what
  the author keeps verbatim, what he expands, what he cuts, how he turns a spoken aside into a
  written caveat.
- **Use:** the Block Synthesizer (24) receives the transformation profile as instructions
  ("When converting Caleb's dictation: keep his first-person asides; add study caveats in the same
  paragraph; favour 'somebody'…"). The Preservation Auditor uses the keep-verbatim patterns.

## 5. The Signature Moves Library (the core transitions and concepts)

**Author directive:** the Ch1 structure is *foundational and modifiable*. Its **core transitions
and concepts** are reused to structure the other chapters. The Voice Lab stores them as a
library, not a rigid template.

`profile/voice_corpus/signature_moves.yaml` is seeded from Ch1 (§8). Each move records:
```yaml
- id: SM-07
  name: "Honest-limits turn"
  function: "pre-empt the strongest objection before the reader raises it"
  exemplar: "If I stopped here, you'd have a tidy chapter and a dishonest one."
  where_used: [ch01 §6]
  use_guidance: "once per chapter, before the costs/evidence climax"
  variation_allowed: true      # wording should vary between chapters; the FUNCTION is what repeats
```
- The Block Architect (24) selects the moves per chapter by function and **varies the wording**.
  A repeated exact phrase across chapters is flagged by the Repetition Manager unless it is a
  deliberate refrain (marked `refrain: true`).
- The author can add, edit, or retire moves in the Voice Lab screen.

## 6. Author controls (the section the author works in)

TUI **Voice Lab** screen + CLI:
- **Add material** with a register, a weight, and a note. It shows "what changed in your voice profile"
  after each addition: the top feature shifts and the confidence gains.
- **Voice Profile view:** the top 25 features by importance, with plain-English descriptions
  ("You follow long sentences with a short punch ~3× more than typical prose"). Confidence
  bars. Register tabs.
- **Pin / relax / forbid:**
  - pin a feature as core ("always keep")
  - relax a feature ("I'm trying to change this")
  - forbid a pattern ("never write 'delve'")

  Pins and forbids override the learned values and are versioned.
- **"Does this sound like me?" check:** paste any text and get VOICE(t) with the explanations
  (the top 5 off-voice features, with sentence highlights).
- **Not-me training:** mark any system output "not me" in one keystroke, and it goes to
  `not_me/` (with confirmation).
- **Snapshots:** the Voice Model is versioned. Compare versions and roll back.

## 7. How the Voice Model feeds the rest of SotS

| Consumer | Uses |
|---|---|
| Style Guide (19 §1.2) | Generated from the model: the top features → dos, the negative features + forbids → don'ts, protected terms, signature moves |
| Style Analyst (19 §5.1) | VOICE(t) and per-hunk fit, with the scaled thresholds |
| Block Synthesis (24) | Transformation profile + signature moves + register-final targets |
| Rewrite Pass A/B | The scaled edit tolerance per feature |
| MGE E6 + panel seats P2/P9 | VOICE(t) + exemplars |
| Audience Lab | The voice floor (scaled) |
| Master Audit T-VOICE / T-REFERENCE | Per-chapter VOICE vs the final register; drift across the book |

## 8. Seed: signature moves observed in Ch1

| ID | Move | Exemplar (Ch1) |
|---|---|---|
| SM-01 | Scene cold open (second person, clock time, sensory detail) | "It's a Tuesday night, a little after eleven." |
| SM-02 | Targeting line | "If that sounds like a regular Tuesday for you, this chapter is for you." |
| SM-03 | Naming a phenomenon | "I call this the post-knowledge paradox." / "so I'll name it" |
| SM-04 | Accusation inventory → reframe | "Now, somebody has already told you what's wrong with you… most of that is a category error." |
| SM-05 | The second half (structure + agency) | "But there's a second half to this, and it's the half most books about our generation skip entirely." |
| SM-06 | Roadmap | "So this chapter starts with… And at the end, I'm going to hand you something to do about it" |
| SM-07 | Honest-limits turn | "If I stopped here, you'd have a tidy chapter and a dishonest one." |
| SM-08 | Pattern hold | "Hold onto that pattern, because it's going to keep showing up" |
| SM-09 | Careful-claim flag | "I want to be careful here" / "I want to be careful with that one" |
| SM-10 | Opinion disclosure | "What follows is my personal opinion… I'd welcome a study that proves me wrong." |
| SM-11 | Self-correction | "including the version of me that wrote the first draft" / "I have to reverse something I said" |
| SM-12 | Science story (claim → critique → replication) | the moral-contagion 2017 → 2021 → 2025 passage |
| SM-13 | Instructions reading | "Read that as a set of instructions" |
| SM-14 | Refrain | "… isn't a character flaw. It's …" (refrain: true) |
| SM-15 | Own case on the table | "I'll put my own case on the table here, because I don't think you should trust a diagnosis from somebody who claims to be immune." |
| SM-16 | Faith stance + invitation | "I believe God exists… if you don't believe it, stay with me anyway" |
| SM-17 | Thought experiment | the bookshelf (credited to Jordan Peterson, heard live in Tulsa, 2024: OI-37) |
| SM-18 | Crisis note | "A note for the reader… 988… findahelpline.com… In my case it was the beginning of one." |
| SM-19 | Instrument framing | "This isn't a hunch dressed up as homework" + the evidence for it + baseline + parts + the notebook |
| SM-20 | "Adapt, but not to nothing" | "Adapt all of this to your actual life… But don't adapt it down to nothing." |
| SM-21 | Bridge | "Where This Leads": a question → the next chapter's case → "This chapter was about… The next one is about…" |

## 9. Routing
```yaml
  voice.annotate_features: {provider: local, temperature: 0.0, max_output_tokens: 2000}
  voice.align_pairs:       {provider: local, temperature: 0.0, max_output_tokens: 2500}
  voice.explain:           {provider: local, temperature: 0.1, max_output_tokens: 800}
  voice.moves_extract:     {provider: muse,  temperature: 0.1, max_output_tokens: 2500}
```
