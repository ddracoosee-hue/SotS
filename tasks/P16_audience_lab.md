# P16 — Audience Lab (Act III)

**Prerequisites:** P15. **Blueprint refs:** 20 (all), 21 (all), 01 R-AUD-01/02.

## Personas
- [ ] **T16.001** | `audience/personas.py` | Load personas.yaml → Persona models; **reject age < 18 (AdultsOnlyViolation)**; cohort birth-year checks (a Gen Z adult must be born 1997–2008 relative to the current year; Millennial 1981–1996; Gen X 1965–1980). | Tests: a 17-year-old rejected; cohort/age mismatch rejected.
- [ ] **T16.002** | `audience/personas.py` | The diversity coverage matrix (20 §4.1) → warnings for uncovered dimensions; the `reviewed` flag surfaced in reports. | Test.
- [ ] **T16.003** | `audience/personas.py` | Cohort weights from config (60/30/10 default); validates the sum = 1. | Test.
- [ ] **T16.004** | `config/personas.yaml` | Review the P00 template set against the coverage matrix; fill gaps; keep neutral ids; write individual backgrounds, not categories. | Loader: 0 coverage warnings.

## Text mechanics metrics (deterministic)
- [ ] **T16.010** | `audience/metrics/phrasing.py` | Jargon rate, cliché hits, corporate words, dated slang, therapy-speak hits, hedging rate, passive-voice rate (heuristic: be-verb + past participle list). | Tests with hand counts.
- [ ] **T16.011** | `audience/metrics/pacing.py` | Sentence stats, paragraph distribution, reading time (238 wpm), hook interval (rule-based candidates: questions, "but"/"then" turns, scene-change markers, numbers after a setup), pull-quote density, information density, dialogue share. | Tests.
- [ ] **T16.012** | `audience/metrics/tonality.py` | The controlling-language index (you + must/should/need to/have to/ought), autonomy index, second-person ratio, exclamation rate, absolutist rate, warmth lexicon score. | Tests.
- [ ] **T16.013** | `audience/metrics/context.py` | Cultural reference inventory with years (from media refs + entities), reference age, US-centric terms, assumption markers. | Tests.
- [ ] **T16.014** | `rewrite/style_analyst.py` | Replace the P15 tonality placeholder with the real tonality metrics. | The P15 tests still pass; a new tone-shift test.

## Mechanics analysts (LLM explains; never invents metrics)
- [ ] **T16.020** | `config/agents/audience_lab/*.yaml` + `prompts/audience/{phrasing,pacing,tonality,context}.v1.md` | Four analyst cards/prompts; the metrics are passed in as data; the output is MechanicsFindings citing unit ids. | doctor validates.
- [ ] **T16.021** | `audience/analysts.py` | Runs the 4 analysts per section; a validator: any `value` in a finding must equal the computed metric (16 §4). | Test: an LLM-altered number → rejected.

## Persona panel
- [ ] **T16.030** | `prompts/audience/persona_read.v1.md` | One prompt for all personas: the persona card injected as data; the adult reader framing; the AC-01…AC-03 rules; the PersonaReaction schema; "respond as a thoughtful adult in plain language". | The prompt validates.
- [ ] **T16.031** | `audience/panel.py` | For each persona × section × sample (3; temperature 0.8; varied seeds/orders) → PersonaReaction. Concurrency-limited; a separate budget slice. | FakeProvider test.
- [ ] **T16.032** | `audience/anti_caricature.py` | Caricature marker scan (AC-02) → reject + regenerate (max 2); a quote requirement (AC-03): every QuoteRef must be a real substring of the section (excerpt check) with a valid unit id. | Tests.
- [ ] **T16.033** | `audience/anti_caricature.py` | Sycophancy check (AC-04): all-positive panel → one re-run with a skepticism reminder. | Test.
- [ ] **T16.034** | `audience/quick_pitch.py` | Quick pitch mode (4 personas × 1 sample on the pitch text) → U3 inputs for the grader. | Test.

## Aggregation, brief, loop
- [ ] **T16.040** | `prompts/audience/takeaway_match.v1.md` + `audience/aggregate.py` | MRR via entailment (full=1, partial=.5); cohort-weighted means/SD/min/max; the journey curve; hotspots (≥ 3 personas); strong lines (≥ 3 personas). | Tests on a synthetic reaction set with hand-computed results.
- [ ] **T16.041** | `audience/aggregate.py` | Panel collapse detection (SD < min_panel_sd) → a low-confidence flag. | Test.
- [ ] **T16.042** | `audience/targets.py` | targets_met(scorecard, chapter reader_journey spec or the global targets). | Tests.
- [ ] **T16.043** | `prompts/audience/brief.v1.md` + `audience/brief.py` | AudienceBrief (≤ 8 priorities, do_not_touch = the strong lines, voice cautions), graded with G-AUD ≥ 95. | Test.
- [ ] **T16.044** | `rewrite/line_editor.py` | `apply_audience_edits(revision, brief)` → audience_edit hunks, respecting do_not_touch + the voice floor. | Tests: a strong-line unit is untouched; a below-floor hunk is rejected.
- [ ] **T16.045** | `acts/act3.py` | The Act III loop (20 §5.3): lab → brief → edits → Gate A → re-test → keep/revert; ≤ 3 loops; unmet targets → a Shadow item + an author notice. | Integration tests: improve-and-keep; regress-and-revert; gate-fail-and-stop.
- [ ] **T16.046** | `reports/sections/audience.py` | Scorecard tables, the journey curve, hotspots, strong lines, and the **"Simulated readers" label** on every block (R-AUD-02). | Snapshot test; a label presence test.

## Real readers + calibration
- [ ] **T16.050** | `audience/questionnaire.py` | Generates a printable questionnaire (Markdown + CSV header) matching the PersonaReaction fields, with an adults-only screening question. | Test.
- [ ] **T16.051** | `audience/calibration.py` | CSV import (rows with age < 18 rejected + counted); per-metric/cohort bias + section-level correlation; the unreliable-metric flag (< 0.3). | Tests.
- [ ] **T16.052** | `cli.py` | `sots audience run|import|questionnaire`. | Tests.
- [ ] **T16.053** | `failsafes/f20_invariants.py` | Register `adults_only`: no persona or imported row < 18 is present in the DB. | Test.
- [ ] **T16.090** | — | All green; BUILD_LOG line. | Done.
