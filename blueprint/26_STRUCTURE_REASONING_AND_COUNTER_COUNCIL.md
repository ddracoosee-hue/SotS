# 26 — STRUCTURE REASONING TEAM + COUNTER-COUNCIL ("Recheck & Reason")

Two agent teams, run **only when the author asks**:
1. **Intent Keepers**: reasoning agents that monitor the structure of the book from the
   **exact psychological perspective of what the author is trying to communicate**.
2. **Counter-Council**: agents built to **counter and challenge** the ideas and the structure.

Both answer to the Master Grading Engine (27). The author sees one master-tested
**Reasoning Report**, not a stream of opinions.

---

## 1. When it runs

- **R-REASON-01 On request only.** Command `sots reason [--scope book|phase|chNN] [--focus structure|ideas|both]`,
  or the TUI "Recheck & Reason" button. It never runs automatically, and it never runs as part
  of an act.
- **R-REASON-02 A reminder, never a nag.** SotS reminds the author that the option exists:
  - the TUI Home and Chapter Board show a small note: *"Recheck & Reason is available: run it
    whenever you want the structure and ideas re-examined (`sots reason`)."*
  - it becomes a highlighted note (still not a popup) when the content changed materially since
    the last reasoning run, e.g. "3 chapters changed since your last Recheck & Reason (Oct 2)".
    Material change = ≥ 10% of units changed, a reorder, or new chapters.
  - the CLI prints a one-line tip after `sots act VI` and `sots export`.
  - `README.md` and `MUSE_START_HERE.md` carry the same note (the "note for the user").
- **R-REASON-03 A run has a dry-run cost estimate and the author confirms it** (it is a large,
  multi-agent run).

## 2. The Author Intent Model (AIM)

The shared ground truth for "what the author is trying to communicate". Both teams read it,
and the MGE's E1 criterion grades against it.

```python
class IntentEntry(BaseModel):
    scope: str                     # "book" | "phase:P3" | "ch11" | "ch11.B4"
    intended_move: str             # the psychological move, e.g. "from 'I am a mistake' to 'I made a mistake'"
    reader_state_before: str
    reader_state_after: str
    emotional_register: str        # e.g. "tender, unflinching, no pity"
    must_not_feel_like: list[str]  # e.g. ["a sermon", "a diagnosis", "blame"]
    evidence: list[str]            # the brief block / author answer / message ids this is derived from
    confirmed_by_author: bool

class AuthorIntentModel(BaseModel):
    version: int
    entries: list[IntentEntry]
```
- Built by the **Intent Cartographer** from the Foundation Layer (briefs' structural purposes,
  old→new beliefs, messages, the architecture's arc roles, the author's own answers). **Every
  entry is a draft until the author confirms it** (TUI Intent screen). Unconfirmed entries are
  used, but flagged as provisional in reports.
- Stored at `profile/intent_model.yaml` (a foundation file, R-FOUND-02).

## 3. Team A: Intent Keepers (structure reasoning)

| Agent | Reasons about |
|---|---|
| **Intent Cartographer** | Builds and updates the AIM; detects drift between the AIM and the current text |
| **Arc Reasoner** | Does the reading order still produce the planned arc (intensity curve, phases, climax placement, denouement)? Checks the book_architecture roles against the actual chapter content |
| **Psychological Sequencing Reasoner** | Does each chapter find the reader in the state the previous chapters produced? Are defenses anticipated before challenges (e.g. safety before shame, grace before service)? |
| **Belief-Shift Reasoner** | For each chapter's old→new belief: is the shift *earned* by the story, mechanism, and evidence in the text? |
| **Thread & Motif Reasoner** | Motif serials, callbacks, the staging of the author's arc, the "braver ending" thread, forward references, and the **Promise Ledger**: every forward promise the text makes (e.g. Ch1: "later in this book I'm going to take [the provocation spiral] apart") must have a chapter that keeps it. Unkept promises are HIGH findings |
| **Pressure & Load Reasoner** | Emotional load and practice (protocol) load across the reading order; where the reader is likely to stop |

Each produces `StructureFinding`s:
```python
class StructureFinding(BaseModel):
    id: str; agent: str; scope: str
    finding: str
    intent_entry_ids: list[str]        # which intended move is at stake
    evidence_unit_ids: list[str]
    severity: Severity
    recommendation: str                # structural direction (reorder, move, cut, bridge), not prose
```

## 4. Team B: the Counter-Council (challenge)

Eight challengers, each with a distinct worldview, so the disagreement is real and not
cosmetic.

| Seat | Challenger | Attacks |
|---|---|---|
| C1 | **Steelman Opponent** | The strongest possible argument *against* each core message (M1–M7) |
| C2 | **Empirical Skeptic** | Evidence gaps, overreach from studies, causal leaps (e.g. "phones cause the crisis" vs the contested research) |
| C3 | **Clinical Caution Reviewer** | Where the advice could harm a vulnerable reader (shame work without support, relapse, crisis) |
| C4 | **Secular Humanist Critic** | Faith framing from a non-believer: is the argument still valid without the theology? Where does it exclude? |
| C5 | **Theological Critic** | From *within* the Christian tradition (e.g. Reformed, Catholic, Orthodox, Wesleyan readings of grace, soul, and works). Is the theology sound and fairly presented? |
| C6 | **Contrarian Structural Editor** | Argues for a different order, merges, cuts, and length; attacks repetition |
| C7 | **Cultural & Generational Critic** | Overgeneralizing about Gen Z / Millennials, moral-panic framing, class and cultural blind spots |
| C8 | **The Reader Who Disagrees** | A thoughtful adult reader who rejects the premise, speaking as a reader, not as an expert |

```python
class Challenge(BaseModel):
    id: str; seat: str; scope: str
    target: Literal["idea", "structure", "evidence", "ethics", "theology"]
    claim_challenged: str               # quote or message id
    argument: str                       # ≤ 300 words
    evidence_ids: list[str]             # verified sources where the challenge is empirical (R-TRUTH-02)
    strength: float | None              # set by the MGE (profile `challenge`)
```

## 5. The reasoning protocol (a deliberation, not a pile of opinions)

```
R0  Load: the AIM + the Foundation + the current manuscript state (latest accepted revisions)
R1  Intent Keepers analyze (in parallel)            → StructureFindings
R2  Counter-Council challenges (in parallel, blind to R1) → Challenges
R3  MGE grades every Challenge (profile `challenge`): drop the weak ones (< 70); keep the strong
R4  Intent Keepers respond to each strong Challenge: DEFEND (with reasons + evidence),
    CONCEDE (propose a change), or REFRAME (partially valid; propose a refinement)
R5  The challenger gets one rebuttal
R6  MGE grades each exchange (profile `deliberation`) → outcome per challenge:
    defended | revise | open (genuinely unresolved: the author decides)
R7  Synthesis → one Reasoning Report, graded by the MGE (profile `reasoning_report` ≥ 95)
```
- Failsafes: the round caps are fixed. There is no endless debate: at most one rebuttal per
  challenge (F04 applies).
- The challengers **never edit the text**. Their conceded points become Proposals (18) or
  structural recommendations for the author.
- R-REASON-04: the Counter-Council's job is to make the book stronger, not to "win".
  Challengers are scored on quality, not on how many points they win.

## 6. The Reasoning Report (what the author sees)

1. **Intent check**: for each chapter, is the intended psychological move landing? (✔ / ⚠ /
   ✘ with evidence)
2. **Structure verdict**: does the reading order still hold? Recommended adjustments, if any.
3. **The strongest challenges**: the top ≤ 10, each with the defense and the outcome.
4. **Open questions for the author**: the genuinely unresolved ones only.
5. **Proposed changes**: as Proposals (graded ≥ 95) on the Proposal Desk.
6. **Changes since the last run**: a diff of findings vs the previous Reasoning Report.

Stored at `data/runs/<run>/reasoning/report.md`, with a history kept for comparison.

## 7. Routing
```yaml
  reason.intent_cartographer: {provider: muse, temperature: 0.1, max_output_tokens: 3000}
  reason.keeper:              {provider: muse, temperature: 0.2, max_output_tokens: 2500}
  reason.challenger:          {provider: muse, temperature: 0.5, max_output_tokens: 2000}
  reason.respond:             {provider: muse, temperature: 0.2, max_output_tokens: 1500}
  reason.synthesize:          {provider: muse, temperature: 0.1, max_output_tokens: 4000}
```
