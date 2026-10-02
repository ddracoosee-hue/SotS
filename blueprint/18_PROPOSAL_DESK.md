# 18 — PROPOSAL DESK (agents bring projects to the author)

The fact-check and expansion teams don't only report. They **pitch**. When they come
across something worth adding (a film that echoes a chapter's theme, a court case that
proves a point better, a study that complicates a claim, a concept bridge between two
chapters), they build a **Proposal**. They ask the author targeted questions about it,
and offer concrete options for **whether, how, and where** to incorporate it.

Every proposal must pass the Quality Gate (17, G-PROP, ≥ 95) before the author sees it.

---

## 1. Who proposes

| Source team | Agent | Proposal kinds |
|---|---|---|
| Fact-check (06 §9) | **Discovery Scout** | `stronger_evidence`, `correction`, `case_study`, `statistic`, `counterpoint` |
| Fact-check (06 §9) | **Media Scout** | `media_echo` (a work that mirrors the author's theme), `media_contrast` (a work that argues the opposite), `media_context` (background on a work the author already cites) |
| Expansion (11) | Explorer + Report Writer | `research_finding`, `concept_bridge`, `deepening`, `new_message_candidate` |
| Expansion (11) | Dialogist | `story_prompt` (a question that could unlock a personal story), `reader_question` |
| Psyche/Shadow | Shadow Self | `reflection_prompt` (only as questions, R-PSY-03) |

## 2. Data model (`src/sots/models/proposal.py`)

```python
class PlacementOption(BaseModel):
    id: str                               # "P1", "P2", …
    location: Literal["after_unit", "before_unit", "replace_unit", "new_section",
                      "sidebar_box", "endnote", "epigraph", "chapter_opening", "chapter_closing"]
    anchor_unit_id: str | None
    chapter_id: str
    rationale: str                        # why here: flow, message, emotional beat
    preview_outline: list[str]            # ≤ 5 bullets of what would go there (NOT prose)

class IntegrationMode(BaseModel):
    id: str                               # "M1", "M2", …
    mode: Literal["brief_mention", "paraphrase_with_citation", "short_quote_with_citation",
                  "extended_example", "author_reflection_on_it", "framing_device",
                  "data_callout", "endnote_only"]
    description: str
    word_estimate: int

class AuthorQuestion(BaseModel):
    id: str
    question: str
    purpose: Literal["experience", "opinion", "memory", "permission", "preference", "fact"]
    required: bool                        # must be answered before integration

class Proposal(BaseModel):
    id: str                               # prop_...
    run_id: str
    kind: str                             # from §1
    source_agent: str
    title: str                            # ≤ 12 words
    pitch: str                            # ≤ 120 words: what was found and why it matters
    what_was_found: list[ReportStatement] # origin-labeled, cited (11 §3)
    connects_to_units: list[str]          # the author's words it relates to
    message_ids: list[str]
    media_work: MediaWork | None          # for media_* kinds
    placements: list[PlacementOption]     # ≥ 2
    modes: list[IntegrationMode]          # ≥ 2
    questions: list[AuthorQuestion]       # 2–5, specific
    risks: list[str]                      # legal pre-screen, audience, voice, factual caveats
    grade_id: str                         # must be passing
    status: Literal["queued", "presented", "discussing", "accepted", "modified",
                    "deferred", "rejected", "integrated", "withdrawn"]
    priority: float

class ProposalDecision(BaseModel):
    proposal_id: str
    decision: Literal["accept", "modify", "defer", "reject"]
    placement_id: str | None
    mode_id: str | None
    answers: dict[str, str]               # question id → the author's answer
    author_notes: str
    reject_reason: Literal["not_my_voice", "off_message", "dont_trust_source", "too_much",
                           "already_covered", "personal_reasons", "legal_worry", "other"] | None
    decided_at: datetime
```

## 3. Question design rules (for the media and discovery scouts)

The questions are the heart of the pitch. They must be **specific to the author's
relationship with the material**. Generic questions are rejected by the validator.

Required question patterns for `media_*` proposals (use at least 2):
- **Exposure:** "Have you watched/read/heard *<work>*? If so, when, and what stayed with you?"
- **Resonance:** "In *<work>*, <specific character/scene> faces <specific situation>. Does that
  mirror what you describe in '<short quote of the author's unit>'?"
- **Stance:** "Critics read *<work>* as <established reading>. Do you agree, or do you see it
  differently?"
- **Use:** "Would you want this as a brief nod, a full comparison, or a framing device for the
  chapter?"
- **Boundaries:** "Is there anything about this work you would *not* want associated with your
  story?"

For `stronger_evidence` / `correction` / `statistic` / `case_study`:
- "Your draft says <X>. The strongest source says <Y> (<source>, <year>). Would you like to
  (a) correct it to Y, (b) keep your framing and add Y as context, or (c) drop the claim?"
- "Did you have a specific source in mind when you wrote this?" (It may be a supplement the
  system hasn't seen yet.)

Validator (`proposals/question_check.py`):
- Each question must mention a concrete element: a named work, character, case, number, or
  a quote of the author's unit (≤ 25 words).
- No leading questions that presume a feeling ("Doesn't this make you angry?").
- 2–5 questions. At least 1 `required`.

## 4. The desk workflow

```
generate → grade (G-PROP) → regenerate ≤ 4 → queue → present → discuss → decide → plan → Pass B
```

1. **Queue management** (`proposals/queue.py`, deterministic):
   - Maximum `proposal_desk.max_open` (default 7) presented at once, so the author isn't
     flooded. The rest wait.
   - Priority = `grade_score/100 × message_priority_weight × novelty × (1 − effort)`.
   - Deduplication: proposals about the same work/case/concept are merged before grading.
   - Proposals for a chapter that is currently in the Legal Chamber (Act IV) are held until
     Act IV finishes for that chapter.
2. **Present** (TUI "Proposal Desk" screen): the card shows the title, pitch, found
   material (with origin colors), the author's connected units, placements, modes,
   questions, risks, and the grade breakdown.
3. **Discuss** (optional): the author can open a chat with the proposing agent. It uses the
   Dialogist runtime (11 §4.5), grounded in the proposal's evidence. The chat may produce an
   updated proposal. A *changed* proposal is re-graded before it is shown again.
4. **Decide**: accept (choose a placement + mode, answer the required questions), modify (the
   answers go back to the producer → regenerate → re-grade), defer (it comes back after N
   runs), or reject (with a reason).
5. **Plan**: an accepted proposal becomes an `IntegrationPlanItem`, consumed by Pass B (19 §4):
   ```python
   class IntegrationPlanItem(BaseModel):
       id: str; proposal_id: str; chapter_id: str
       placement: PlacementOption; mode: IntegrationMode
       author_answers: dict[str, str]     # personal material the Weaver may use (in the author's words)
       evidence_ids: list[str]
       status: Literal["planned", "woven", "verified", "failed"]
   ```
6. **Learning**: decisions and reject reasons feed the grader calibration (17 §6) and the
   scouts' prompt tuning (20 §7). Example: if `not_my_voice` dominates, the voice
   compatibility floor rises (proposed to the author, not automatic).

## 5. CLI
`sots proposals list [--status queued]`, `sots proposals show <id>`,
`sots proposals decide <id> --accept P1 M2 --answer q1="…"`,
`sots proposals archive` (the below-bar items).
