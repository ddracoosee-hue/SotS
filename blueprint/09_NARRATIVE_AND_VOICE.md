# 09 — NARRATIVE, MESSAGES, AND VOICE (Stage 8)

**Goal:** keep the author on track. Show which core messages each passage serves, where the
writing drifts, where the flow breaks, and whether it sounds like the author.

## 1. Core messages (`profile/messages.yaml`)

```yaml
book:
  - {id: M1, statement: "…", priority: 1}
  - {id: M2, statement: "…", priority: 2}
chapters:
  ch01:
    - {id: C1.1, statement: "…", priority: 1}
```
> These are filled in **together with the author** after the chapter briefs arrive
> (see `15_OPEN_ITEMS.md`). Until then, `sots profile check` reports "messages missing",
> and stage 8 runs only the voice and flow parts.

## 2. Message ledger (`narrative/ledger.py`, task `narrative.map_messages`)

- Batches of 25 units, with the book + chapter messages in context.
- Output: one `MessageMapping` per unit (`03 §6`).
- **Most important messages** view: rank the messages by
  `sum(strength × role_weight)` across units, where the role weights are
  states 1.0, illustrates 0.9, supports_with_evidence 0.9, counters 0.5, transitions 0.2,
  none 0. This shows what the text is *actually* emphasizing vs what the brief says it
  *should* emphasize (priority).
- Emphasis gap = the rank difference between actual emphasis and brief priority. Show the
  top gaps.

## 3. Drift (`narrative/drift.py`, deterministic)

- `unmapped_ratio` = units with message_id None ÷ all units (NARRATIVE_DEVICE units
  excluded).
- `drift_segments`: runs of ≥ 5 consecutive units where ≥ 80% are unmapped.
- `missing_messages`: chapter messages with no unit whose role is `states` or `illustrates`.
- For an unsorted word vomit (no chapter_id): score the units against every chapter's
  messages. Suggest the best-fitting chapter per drift segment ("this section may belong
  in ch04").

## 4. Flow (`narrative/flow.py`)

- A deterministic pass over consecutive unit pairs: flag a jump when the message_id changes
  **and** the emotion changes sharply (from the stage 7 emotion findings) **and** neither
  unit is a `transitions` role.
- The flagged pairs go to the LLM in one batched call, which confirms or rejects each break
  and describes what bridge is missing (it does not write the bridge).
- Output: `flow_breaks` in the `DriftReport`.

## 5. Voice (`narrative/voice.py`)

> **Superseded by `29_VOICE_LAB.md`**, which adds a confidence-weighted Voice Model with
> scaled assessments. The fingerprint below stays as the minimal baseline feature set:
> 29 §2 extends it to 120+ features, and 29 §3.5 replaces the similarity formula.

### 5.1 Fingerprint (deterministic part)
Compute a `VoiceFingerprint` from the Voice Lab corpus `profile/voice_corpus/` (29; formerly `style_samples/`) (the author's reference voice)
and from the current document:
- sentence length mean/stdev (split on `.!?` + newline, keeping abbreviations intact with a
  small exception list)
- type-token ratio (on the first 5000 words, to stay comparable)
- punctuation per 1000 words: `, ; : — - ! ? … ( "`
- pronoun shares: first person (I/me/my/we/us/our), second person (you/your), third person
- `signature_phrases`: the top 20 word 3-grams in the samples that appear in fewer than
  3 of the other documents (a crude "idiolect")

### 5.2 Style description + comparison (task `narrative.voice`)
- Once per style-sample set: the LLM writes a `llm_style_description` (≤ 200 words) from
  3 sample excerpts. Cached until the samples change (hash of the folder).
- Per document: `similarity = 0.5 × numeric_similarity + 0.5 × llm_similarity`.
  - numeric_similarity = 1 − mean of the normalized absolute differences across the
    fingerprint metrics, each clipped to [0, 1]
  - llm_similarity: the LLM rates 0–1, and lists `deviations` and the `off_voice_unit_ids`
- Rule: voice checks **describe** differences. They never rewrite text (R-SCOPE-02).

## 6. What the author sees
- **Messages** screen: a coverage bar per message, the emphasis-gap list, and missing
  messages in red.
- **Drift map**: the document as a strip of units colored by message; drift segments are
  outlined.
- **Voice** panel: the similarity score, the top deviations, and a list of off-voice
  passages.
