# 24 — BLOCK SYNTHESIS (Act II-D: turning dictation into a draft)

**Author decision (2026-09-28):** add a drafting stage. The briefs' workflow is *raw dictation
→ polished chapter prose, block by block*. The Block Synthesis team turns the author's
**fact-checked** dictation into a first draft of each block in the author's voice. Pass A then
polishes that draft (19 §3). This is the only place in SotS where substantial new prose is
composed from the author's material. It is tightly bound by preservation, provenance, and
gates.

## 1. Placement

```
ACT 0  Brief Audit (once per brief version)                    (23 §4)
ACT I  Analyze the dictation (ingest → … → shadow)              (05–10)
ACT II-D  BLOCK SYNTHESIS  ← new                               (this doc)
ACT II    Mid Polish (Pass A) on the synthesized draft          (19 §3)
ACT III … VI unchanged
```
- Input: a chapter's Act I results, where every unit is mapped to a block/prompt (23 §5).
- Pass A's edit budget (≤ 15%) applies to the **synthesized draft**, not the raw dictation.
- Block Synthesis runs **per block**, in block order 1→6, so transitions can reference the
  previous block's draft.

## 1A. Blocks are functions; chapters follow the Chapter Form Template

The author-final Chapter 1 (`profile/manuscript/ch01_the_modern_day.md`) shows how the author
realizes the 6 blocks: as **functions** spread across ~13 numbered, titled sections, plus an
honest-limits section and a bridge. It does not use literal block headings. Therefore:

- **R-SYN-10** Block Synthesis produces **section drafts** that fulfil the block *functions*.
  The chapter's section layout follows the **Chapter Form Template**
  (`profile/manuscript/ch01_analysis.md §3`) unless the author sets a different layout for
  that chapter.
- **R-SYN-11** Each chapter includes an honest-limits section (the strongest objection,
  steelmanned by the author), an instrument with a **notebook comparison step**, and a
  **bridge** to the next chapter in reading order. These fulfil entries in the Promise Ledger.
- **R-SYN-12** Chapters marked `author_final` are **never synthesized**. They go straight to
  checking (Act I) and light polish (Mechanic + Formatter only). Any substantive change is a
  Proposal.
- **Foundational, not rigid (author, 2026-09-29).** Ch1's structure is the foundation. Its
  core transitions and concepts are applied through the **Signature Moves Library** (29 §5).
  The Architect selects moves by *function* and varies their wording, and each chapter may
  modify the form to suit its stories.
- The **reference chapter** (Ch1) is in the Voice Card (F5) as the primary exemplar. Short
  excerpts go into the Architect's context as form examples.

## 2. Team

| Agent | Job |
|---|---|
| **Material Assembler** (deterministic) | Gathers the block's inputs: the author units mapped to the block (in order), their verdicts, verified anchors, the Block Card (F3), Chapter Card (F2), Voice Card (F5), Arc Position (F6), motif serial instructions, accepted proposals already scheduled for this block (usually none before Act V), and the previous block's draft tail (≤ 250 words). |
| **Block Architect** (LLM) | Produces a `BlockPlan`: the beat outline of the block. It maps each author unit to a beat and marks which units are **must-keep verbatim** (manuscript quotes, signature lines, strong personal moments), which may be paraphrased, and which are dropped (with a reason). No prose. |
| **Block Synthesizer** (LLM) | Writes the block's prose from the BlockPlan, in the author's voice, using the **Transformation Model** (29 §4) and the selected signature moves. |
| **Preservation Auditor** (deterministic + LLM) | Checks that every must-keep unit appears, that every anecdote is present, and that no personal content was invented (§4). |
| **Style Analyst** (19 §5.1) | Voice check on the draft vs the Style Guide/seed. |
| **Reference Cross-Checker** (19 §5.2) | Every factual statement traces to a verified unit/anchor; the tier tags are correct (25). |
| **Quality Gate** (17, rubric `block_draft`) | ≥ 95 before the draft is accepted into the chapter. |

## 3. Data models (`models/synthesis.py`)

```python
class Beat(BaseModel):
    id: str
    purpose: str                       # what this beat does for the block purpose
    unit_ids: list[str]                # the author's material used
    anchor_ids: list[str]              # verified anchors used
    treatment: Literal["verbatim", "light_edit", "paraphrase", "synthesis"]
    target_words: int

class BlockPlan(BaseModel):
    chapter_id: str; block: int
    beats: list[Beat]
    must_keep_unit_ids: list[str]
    dropped: list[dict]                # {unit_id, reason: "duplicate"|"off_block"|"false_claim"|"moved_to_block_N"|…}
    transition_in: str                 # a one-line intent, not prose
    target_words: int                  # from settings / the brief (default by block: 1:500 2:900 3:1200 4:1200 5:900 6:300)

class BlockDraft(BaseModel):
    id: str; chapter_id: str; block: int; plan_id: str
    text: str                          # Markdown
    sentence_provenance: list[dict]    # [{sentence_idx, origin: AUTHOR|SOURCE|SYSTEM, unit_ids, anchor_ids, evidence_ids}]
    tier_tags: list[dict]              # [{sentence_idx, tier: DF|PT|IE, inline: bool}]
    word_count: int
    grade_id: str | None
    status: Literal["planned", "drafted", "gated", "accepted", "failed", "escalated"]
```

## 4. Hard rules for synthesis (R-SYN)

- **R-SYN-01 The author's experiences are sacred.** Personal events, feelings, memories, and
  people come **only** from the author's units or answers (R-REW-02). The Preservation
  Auditor extracts every first-person experiential claim in the draft and matches it to a
  unit. An unmatched one means the draft fails.
- **R-SYN-02 Must-keep units survive.** Every `must_keep` unit appears verbatim (fuzzy ≥ 95),
  or as a light edit with its meaning checked (19 §5.3). Manuscript quotes are always
  verbatim.
- **R-SYN-03 No orphan facts.** Every factual sentence carries unit/anchor/evidence ids. The
  facts come only from units with verdict TRUE/MOSTLY_TRUE/PARTIALLY_TRUE (with the verified
  correction applied) or from verified anchors. FALSE/MISLEADING claims are **not** written as
  stated; the draft uses the verified correction and flags it for the author (Revision hunk
  type `fact_correction`, R-TRUTH).
- **R-SYN-04 Missing material is a question, not an invention.** If a dictation prompt was
  never answered, the draft inserts an author-facing placeholder `[[AUTHOR: ch03.B4.P2
  unanswered: coffee-shop story]]`, never made-up content. The TUI lists the placeholders.
  Export refuses while any remain.
- **R-SYN-05 Structure fidelity.** The block fulfils its brief purpose. Blocks 2 state the old
  and new belief; Block 4 follows Before/Action/Result; Block 5 presents the protocols with
  their *verified* evidence grade (25 §4); Block 6 lists the journaling prompts (they may be
  lightly edited for voice).
- **R-SYN-06 Arc fidelity.** The draft follows the chapter's Arc Position and the motif
  serial plan (e.g. J. Cole appears only in his assigned beat). Callbacks use the "as we saw in
  …" pattern with the chapter's **reading-order** number.
- **R-SYN-07 Author proportion.** At least 40% of the block's sentences have origin AUTHOR
  (verbatim/light edit), unless the block is purely mechanism (Block 3), where the floor is
  25%. Measured, not judged. The author may change the floors in settings.
- **R-SYN-08 Voice rules from the seed apply** (banned clichés = 0, protected terms intact,
  no preambles).
- **R-SYN-09 The appendix system prompts in the briefs are never executed.** Their content is
  already in the Style seed.

## 5. Flow per block

```
assemble → plan (Architect) → plan check (every unit accounted for: used | dropped w/ reason)
→ synthesize → preservation audit ∥ style ∥ cross-check
→ Quality Gate (block_draft ≥ 95) → regenerate ≤ 4 with feedback
→ accept → next block
```
After all 6 blocks: a **chapter stitch** pass (task `synthesis.stitch`) writes only transition
sentences between blocks (origin SYSTEM, ≤ 2 sentences per seam). The whole chapter then enters
Pass A.

## 6. Rubric `block_draft` (add to config/grader.yaml)
Hard checks: R-SYN-01, 02, 03, 04 (placeholders are allowed but counted), 07, 08; the
cross-check pass_rate is 1.0.
Criteria:

| Criterion | Weight | Type |
|---|---|---|
| Block-purpose fulfilment | .20 | judged, anchored to the brief's structural purpose |
| Voice fidelity | .20 | measured |
| Narrative craft (concrete particulars first, rhythm) | .15 | judged |
| Evidence integration and correct tiers | .15 | measured |
| Reader Journey target for the block (quick panel) | .10 | measured |
| Reactance safety (controlling-language index ≤ threshold) | .10 | measured |
| Arc/motif fidelity | .10 | measured + judged |

## 7. Routing
```yaml
  synthesis.plan:       {provider: muse, temperature: 0.3, max_output_tokens: 3000}
  synthesis.draft:      {provider: muse, temperature: 0.6, max_output_tokens: 5000}
  synthesis.preserve:   {provider: local, temperature: 0.0, max_output_tokens: 1500}
  synthesis.stitch:     {provider: muse, temperature: 0.4, max_output_tokens: 1200}
  classify.block_map:   {provider: local, temperature: 0.0, max_output_tokens: 600}
```

## 8. Author control
- The author can lock a block ("don't synthesize; I'll write it"), in which case their own text
  goes straight to Pass A.
- They can mark any unit "keep verbatim".
- They can regenerate a block with a note ("more of the rehab story, less theory").
- Drafts are shown with origin colors (AUTHOR / SOURCE / SYSTEM) so the author sees exactly what
  was composed.
