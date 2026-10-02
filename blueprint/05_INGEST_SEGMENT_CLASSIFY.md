# 05 — STAGES 1–3: INGEST, SEGMENT, CLASSIFY

> **Foundation update (23 §5):** dictation may be keyed to chapter/block/prompt
> (`### ch03.B2.P1`). Units carry `block`, `prompt_id`, and `anchor_ids`. Unmarked units are
> block-mapped by `classify.block_map`. A dictation-coverage report lists the answered and
> missing prompts.

## Stage 1 — INGEST (`ingest/`)

**Input:** a file path (`.txt`, `.md`, `.docx`, `.pdf`), or text pasted in the TUI (saved
to a temporary `.md` file first).
**Output:** one `Document` row plus an immutable copy in `data/inbox/<doc_id>.<ext>` and
`data/inbox/<doc_id>.txt` (the extracted plain text).

Steps:
1. Compute SHA-256 of the file bytes. If a document with the same hash exists, ask
   (in the CLI/TUI) whether to reuse it or create a new document. Default: reuse.
2. Copy the file into the inbox. Extract the text:
   - `.docx` → python-docx paragraphs joined by `\n\n`
   - `.pdf` → pypdf page text. If the result has fewer than 50 characters per page, warn
     "scanned PDF, OCR not supported".
   - `.txt` / `.md` → read as UTF-8 (fall back to cp1252 on a decode error).
3. Normalize (`normalize.py`): convert all line endings to `\n`, turn non-breaking spaces
   into plain spaces, and collapse 3+ blank lines into 2. **Do not change the words,
   spelling, or punctuation.** Typos stay; they are the author's text.
4. The extracted `.txt` is the canonical text. All `start_char`/`end_char` values refer
   to it.
5. Ask for (or accept via `--chapter`) the `chapter_id`. It may be `None` for unsorted
   word vomit. Stage 8 then suggests the best-matching chapter.

## Stage 2 — SEGMENT (`segment/`)

**Goal:** turn the text into **atomic units**. One unit = one claim, one story beat, one
belief, one lesson, one media mention, or one question.

### 2.1 Chunk
See `04 §5`. Store the `Chunk` rows.

### 2.2 Extract units (`extractor.py`, task `segment.extract_units`)

Prompt contract (`prompts/segment/extract_units.v1.md`):
- The input is the chunk text, with a character offset ruler: the text is given with the
  chunk's `start_char` so the model can return offsets.
- The model returns `{"units": [{"text": "...", "start": int, "end": int}]}`, where the
  offsets are **relative to the chunk**.
- Instructions to the model:
  - Split compound sentences when they contain more than one checkable claim.
    "Divorce rates hit 50% in the 80s and that's why my parents split" becomes 2 units.
  - Keep a personal story beat together as one unit, even across several sentences, unless
    it contains a factual claim, which is split out.
  - Keep every word. Do not paraphrase. Every unit's text must be an exact substring.

### 2.3 Offset repair (deterministic, required)
LLM offsets are unreliable. For each returned unit:
1. If `chunk_text[start:end] == text`, accept it.
2. Otherwise search for `text` in the chunk. With exactly one match, use it.
3. Otherwise fuzzy-align with rapidfuzz `partial_ratio_alignment`. If the score is ≥ 95,
   use the aligned span and **replace `text` with the actual substring**.
4. Otherwise drop the unit and log `segment.unmatched_unit`.

After repair, check coverage: the units must cover ≥ 85% of the chunk's non-whitespace
characters. If coverage is lower, re-run extraction once on the uncovered spans. Remaining
gaps become units of type `NARRATIVE_DEVICE` with `classify_confidence = 0`, so nothing the
author wrote is silently lost.

### 2.4 Summaries
Build the summary tree (see `04 §5`) after all units are stored.

## Stage 3 — CLASSIFY (`classify/`)

### 3.1 Safety scan first (`safety_scan.py`, task `classify.safety_scan`)
Run in batches of 20 units. Output: `{"flags": [{"unit_id": str, "reason": str}]}`.
Set `unit.safety_flag`. See R-PSY-04. The scan only flags; it never blocks.

### 3.2 Classify each unit (`classifier.py`, task `classify.unit`)

Output model:

```python
class ClassificationOut(BaseModel):
    content_type: ContentType
    claim_kind: ClaimKind | None
    media_kind: MediaKind | None
    checkability: Checkability
    entities: list[str]
    normalized_claim: str | None     # required if checkability != NOT_CHECKABLE
    embedded_claims: list[str]       # checkable facts hidden inside a PERSONAL_* unit
    confidence: float
```

Decision rules. Put these **verbatim in the prompt**, and enforce them again in code
(`classifier.validate_consistency`):

| If… | Then… |
|---|---|
| It describes what happened to the author/their family/friends | `PERSONAL_EXPERIENCE`, `NOT_CHECKABLE` unless `embedded_claims` is non-empty (then `PARTIAL`) |
| It states an opinion, value, or "I believe/feel" | `PERSONAL_BELIEF`, `NOT_CHECKABLE` |
| It tells the reader what to do or what to learn | `LESSON_ADVICE`. If it rests on a factual premise ("studies show…"), the premise goes into `embedded_claims` and checkability is `PARTIAL` |
| It contains a number, percentage, or rate about the world | `FACTUAL_CLAIM` / `STATISTIC` |
| It names a lawsuit, trial, ruling, or legal outcome | `FACTUAL_CLAIM` / `LEGAL_CASE` |
| It describes a viral post, influencer, online controversy, or "a TikTok where…" | `FACTUAL_CLAIM` / `SOCIAL_MEDIA_CASE` |
| It cites research, science, or psychology findings | `FACTUAL_CLAIM` / `ACADEMIC_FINDING` |
| It names or retells a book, film, show, song, game, or podcast | `MEDIA_REFERENCE` with `media_kind` |
| It says "X said…" | `FACTUAL_CLAIM` / `QUOTE_ATTRIBUTION` |
| Metaphor, transition, or a hook with no claim | `NARRATIVE_DEVICE`, `NOT_CHECKABLE` |

Consistency checks in code (a failure triggers a retry, then `FAILED`):
- `claim_kind` is set **if and only if** `content_type == FACTUAL_CLAIM`.
- `media_kind` is set **if and only if** `content_type == MEDIA_REFERENCE`.
- `checkability == NOT_CHECKABLE` means `normalized_claim` is None and
  `embedded_claims` is empty.
- A `MEDIA_REFERENCE` is never `NOT_CHECKABLE`. The retelling is always checkable.

### 3.3 Embedded claims become child units
Each item in `embedded_claims` becomes a new `Unit` with:
- the same `start_char`/`end_char` as its parent (it points to the parent's text),
- `content_type = FACTUAL_CLAIM`, classified again by the same task,
- `entities` inherited from the parent,
- `parent_unit_id` set to the parent unit's id.

### 3.4 Low-confidence queue
Units with `confidence < settings.classify.review_threshold` (default 0.6) appear in the
TUI **Review queue**, where the author can relabel them with one keypress. A human label
always overrides the model and is stored with `labeled_by = "author"`.

## Stage outputs checklist

After stage 3 the database must contain, for the document:
- 1 `Document`, ≥ 1 `Chunk`, ≥ 1 `Unit`
- every `Unit` with non-null `content_type` and `checkability` (or status `FAILED`)
- a complete summary tree ending in exactly one root summary
