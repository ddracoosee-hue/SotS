# 08 — PSYCHE ENGINES (Stage 7)

Six analysis engines examine **the text** (R-PSY-01). They share a blackboard, so each
engine can build on, agree with, or challenge the others. A synthesizer then merges the
results.

## 1. Engines

| Engine | File | Question it answers | Finding types (exact vocabulary) |
|---|---|---|---|
| **Emotion** | `engines/emotion.py` | What emotional tone runs through the text, and where does it shift? | `dominant_emotion`, `emotional_shift`, `intensity_peak`, `flat_passage`, `tone_mismatch` (tone doesn't fit the content) |
| **Cognitive** | `engines/cognitive.py` | What reasoning patterns show up? | `overgeneralization`, `all_or_nothing`, `catastrophizing`, `mind_reading`, `should_statement`, `personalization`, `emotional_reasoning`, `logical_fallacy:<name>`, `sound_reasoning` (positive findings count too) |
| **Theme** | `engines/theme.py` | What is this text really about, underneath the surface? | `explicit_theme`, `implicit_theme`, `recurring_motif`, `theme_conflict` |
| **Archetype & Arc** | `engines/archetype.py` | What story shape and roles appear? | `archetype:<name>` (e.g. mentor, shadow, orphan, warrior, caregiver, trickster), `arc_stage:<name>` (call, refusal, ordeal, return, …), `arc_gap` (a missing stage), `role_of_other` (how other people are cast) |
| **Blind Spot** | `engines/blindspot.py` | What might the text be defending against or not seeing? | `projection_possible`, `rationalization_possible`, `minimization_possible`, `idealization_possible`, `missing_perspective`, `unexamined_assumption` |
| **Reader Impact** | `engines/reader.py` | How will the target reader receive this? | `resonant`, `alienating`, `preachy`, `vague`, `actionable`, `triggering_without_care`, `credibility_risk` |

Rules for every engine:
- Each finding cites ≥ 1 `unit_id`. Code rejects findings without one.
- Blind Spot findings always use the `_possible` form and must include
  `question_for_author` (R-PSY-03).
- Cognitive findings describe the passage ("this passage generalizes from one event to
  all men"). They never label the author.
- Positive findings are required: every engine must report at least one strength when
  one exists. The system is meant to be honest, not only critical.

## 2. The blackboard (`psyche/board.py`)

```python
class Board:
    def post(self, finding: EngineFinding) -> None
    def read(self, engine: str | None = None, unit_ids: list[str] | None = None,
             finding_type_prefix: str | None = None) -> list[EngineFinding]
    def facts_for(self, unit_ids: list[str]) -> list[VerdictRecord]   # stage 5 results
    def media_for(self, unit_ids: list[str]) -> list[MediaCheck]       # stage 6 results
```
The board is stored in the `engine_findings` table, filtered by run_id. The board is
append-only.

## 3. Execution order (`psyche/registry.py`)

```
Layer 1 (parallel, per chunk):   emotion, cognitive, theme
Layer 2 (reads layer 1 + facts): archetype, blindspot
Layer 3 (reads everything):      reader
Then:                            triggers pass → synthesizer
```
- Layer 1 runs once per chunk (a unit list + neighbouring summaries).
- Layer 2 runs per chunk, and receives the layer-1 findings for that chunk's units plus the
  fact/media results for those units.
- Layer 3 runs per document, and receives the root and level-1 summaries plus the top 40
  findings by severity.
- Each engine prompt includes a `BOARD_EXCERPT` variable: the relevant prior findings as
  compact JSON. The engine sets `responds_to` when it builds on one of them.

## 4. Cross-engine triggers (`psyche/triggers.py`)

These are deterministic rules that run after layer 3. Each fired trigger creates an
`EngineFinding` with engine = `"trigger"` and `responds_to` pointing at its sources.

| ID | Condition | Created finding |
|---|---|---|
| TR-01 | Cognitive `overgeneralization` on a unit whose fact verdict is FALSE/MISLEADING | `credibility_risk`, HIGH: "a generalization rests on an inaccurate fact" |
| TR-02 | Emotion `intensity_peak` + Blind Spot finding on the same unit | `sensitive_core`, MEDIUM: likely an emotionally central passage; handle with care in revision |
| TR-03 | Theme `explicit_theme` with fuzzy similarity < 60 to every `key_messages` item in the chapter brief (read directly from the profile, not from stage 8) | `theme_off_brief`, MEDIUM |
| TR-04 | Reader `preachy` on a LESSON_ADVICE unit with no PERSONAL_EXPERIENCE unit within ±5 units | `unearned_lesson`, MEDIUM (also passed to the Shadow Self) |
| TR-05 | Archetype `role_of_other` cast as villain + Cognitive `mind_reading` on the same units | `one_sided_portrayal`, MEDIUM |
| TR-06 | A media check with `contradicted_by_source` used to state a lesson | `media_misuse`, HIGH |
| TR-07 | Emotion `tone_mismatch` on a FACTUAL_CLAIM unit | `rhetorical_charge`: the fact is presented with loaded tone |

New triggers are added as new functions in `triggers.py`, each with an ID and a unit test.

## 5. Synthesizer (`psyche/synthesizer.py`, task `psyche.synthesize`)

Input: all findings (sorted by severity, capped at 120), the trigger findings, and the
root summary.
Output: `Synthesis` (`03 §5`):
- `agreements`: where ≥ 2 engines point at the same units or conclusion
- `tensions`: where engines disagree (e.g. Emotion says "resonant", Reader says
  "alienating"). Tensions are valuable; never hide them
- `top_insights`: at most 7, ranked, each citing finding ids

Code check: every id cited in the synthesis must exist on the board. Otherwise retry.

## 6. What the author sees
- **Psyche Board** screen: filter by engine, severity, or unit; click through to the text.
- **Synthesis** panel: agreements / tensions / top insights.
- A heat strip along the document showing emotional intensity per unit.
