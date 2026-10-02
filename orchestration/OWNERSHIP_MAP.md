# Ownership map

**The rule.** Every path has exactly one owner at any moment. The owner edits the path freely inside
its own lane. Anyone else may edit it only (a) inside their own **anchor block**, (b) when this map
**grants** them that file for a named task and wave (with the owner as reviewer), or (c) through a
**change request** (`COMMUNICATION_PROTOCOL.md §4`). Paths are relative to `src/sots/` unless they
start with `config/`, `prompts/`, `tests/`, `eval/`, `blueprint/`, `tasks/`, or a root file name.

## 1. Lane packages

| Owner | Owns (create and edit freely) |
|---|---|
| **A** Foundation & Voice | `profile/`, `ingest/`, `foundation/`, `segment/`, `classify/`, `voice/`, `synthesis/`; `models/foundation.py`, `models/voice.py`, `models/synthesis.py`; `acts/act2d.py`; `narrative/repetition.py`; `shadow/arc_consistency.py`; `reports/sections/dictation_coverage.py`, `reports/voice_profile.py`; `prompts/{foundation,segment,summarize,classify,synthesis,voice}/`; `config/agents/synthesis/`; `eval/synthesis_gold/` |
| **B** Truth, Evidence & Law | `research/` (incl. `fetchers/`, `search/`), `verify/`, `media/`, `brief_audit/`, `discovery/`, `expand/`, `legal/` (except `legal/delta.py`); `acts/act0.py`, `acts/act4.py`, `acts/act5.py` (producer part); `reports/sections/{claims,media,legal}.py`, `reports/brief_audit.py`; `prompts/{research,verify,fact_check,media,expand,legal}/`; `config/agents/{fact_check,media,discovery,legal_chamber}/`; `config/source_tiers.yaml`, `config/legal.yaml`; `eval/gold/brief_anchors_gold.yaml`, `eval/legal_gold/` |
| **C** Judgment & Craft | `grader/`, `mge/`, `rewrite/`, `proposals/`, `audit/`; `models/mge.py`, `models/section.py`; `acts/act2.py`, `acts/act6.py`, `acts/act5.py` (desk part, from W3); `legal/delta.py` (W4); `reports/manuscript.py` (from W4), `reports/master_audit.py`, `reports/sections/proposals.py`; `config/grader.yaml`, `config/mge.yaml`, `config/formatting.yaml`; `agents/tools/languagetool.py` (from W2); `prompts/{grader,mge,rewrite,proposals,audit}/`; `config/agents/{quality_gate,rewrite_pass_a,rewrite_pass_b,proposal_desk}/`; `eval/{grader_gold,rewrite_gold,proposal_gold,mge_calibration,master_battery}/` |
| **D** Pipeline & Mind | `psyche/`, `narrative/` (except `repetition.py`), `shadow/` (except `arc_consistency.py`), `pipeline/`, `audience/`, `learning/`, `reason/`, `tui/` (shell + D screens); `acts/chapter_state.py`, `acts/act1.py`, `acts/act3.py`; `models/reason.py`; `reports/markdown.py`, `reports/export.py`, `reports/sections/{psyche,narrative,shadow,audience}.py`; `eval/run_eval.py` (the runner; others register metrics); `prompts/{psyche,narrative,shadow,audience,learning,reason}/`; `config/agents/{psyche,narrative,shadow,audience_lab,learning,reason}/`; `config/personas.yaml`, `config/audience/`, `config/rubrics.yaml`, `config/system_goals.yaml`, `config/safety.yaml` |
| **I** Integrator (shared infrastructure) | `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `.python-version`; `BUILD_LOG.md`; `blueprint/15_OPEN_ITEMS.md` (append only); `tasks/00_TASK_INDEX.md` (cross-cutting boxes); `cli.py` (root wiring); `config.py`; `config/settings.yaml`, `config/routing.yaml`, `config/teams.yaml`; `storage/` (the core, `schema.sql`, `migrations/`); `models/` (every module that existed at `w0-baseline`); `providers/`; `agents/` runtime (`base.py`, `cards.py`, `events.py`, `registry.py`, `grading.py`, `failsafes/`, `tools/`); `errors.py`, `logging_setup.py`; `tests/conftest.py`, and every test file that existed at `w0-baseline`; `vault/`; `orchestration/` |
| **Author only** | `profile/**` (R-FOUND-02; lanes read it through the junction, and changes go through Proposals), `MUSE_START_HERE.md` (OI-04), `blueprint/**` except the 15 append (R-SCOPE-04), `supplements/`, `.env` |

Each lane also owns the tests and fixtures it creates (§5) and its own lines in `tasks/<its phase>.md`
(checkbox edits only, R-SCOPE-04).

## 2. Files shared across lanes (from the task-to-file cross-reference)

| File | Tasks (lane) | Rule |
|---|---|---|
| `cli.py` | 25 tasks, all lanes | **W0 splits it.** Command bodies move to `commands/<domain>.py` (each lane owns its own). `cli.py` keeps only wiring, and each lane adds its registration lines inside its anchor block. |
| `agents/failsafes/f20_invariants.py` | T03.059 (I), T04.016, T05.010 (A), T07.037 (B), T14.034, T15.003 (C), T16.053 (D), T17.034 (B), T20.025 (C) | **W0 adds** `register_invariant(name, fn)`. Each lane defines its invariants in `<package>/invariants.py` and imports them in its anchor block of `agents/failsafes/invariant_plugins.py`. The core file stays frozen. |
| `agents/base.py`, `agents/cards.py` | P03 (I), T04A.022 (A), T14.025, T14M.043 (C) | **W1 designated editor: C.** A's T04A.022 goes in as contract K2 (a CR to C). From W2 on, the owner is I again. |
| `providers/context_pack.py` | T02.020–022 (I), T04A.021 (A) | **Granted to A for T04A.021 in W1.** After that, each lane adds the TASK_PIECES entries for its own routing tasks inside its anchor block. |
| `agents/tools/*` | P03 (I), T07.036 (B), T15.020 (C) | **Granted:** B for T07.036 (W1), C for `languagetool.py` (W2). |
| `agents/failsafes/f13_injection.py` | T03.052 (I), T18.027 (B) | T18.027 is a **test** only; B adds `tests/unit/test_expand_injection.py` and does not edit the module. |
| `classify/review_queue.py` | T06.006 (A), T09.008 (B) | T09.008 is **deferred to W2**; A reviews. |
| `profile/loader.py` | T04.001–002 (A), T18.004 (B) | **Granted to B for T18.004 in W2**; A reviews. |
| `rewrite/style_guide.py` | T15.010–011 (C, W2), T11A.032 (A, W3) | **Granted to A for T11A.032 in W3**; C reviews. |
| `rewrite/cross_checker.py` | T15.062–065 (C, W2), T14A.017, T14A.029 (A, W3) | **Granted to A in W3**; C reviews. |
| `rewrite/style_analyst.py`, `rewrite/line_editor.py` | P15 (C, W2), T16.014, T16.044 (D, W3) | **Granted to D in W3**; C reviews. |
| `rewrite/mechanic.py`, `formatter.py`, `gates.py` | P15 (C), P20 (C) | The same lane both times, so no rule is needed. |
| `acts/act2.py` | T15.071–072 (C, W2), T14A.022 (A, W3) | **Granted to A for T14A.022 in W3**; C reviews. |
| `acts/act5.py` | T18.028 (B, W2), T19.010 (C, W3) | Separate functions per part. C owns the file from W3. |
| `reports/manuscript.py` | T14A.023 (A, W3), T20.022–023 (C, W4), T24.023 (C, W6) | A creates it in W3; ownership moves to C at M3. |
| `pipeline/dry_run.py` | T13.005 (D, W2), T24.002 (C, W6) | **Granted to C in W6**; D reviews. |
| `eval/run_eval.py` | T13.011 (D), T14.032, T15.074 (C), T17.033 (B), T19.013 (C), T23.001–002 (D) | D's K4 creates a **metric registry**. Every other lane registers its metric from `<package>/eval_metrics.py` and adds one import line in its anchor block. |
| `config/grader.yaml` | P00 (I), P14 (C), T14A.002 (A, W3) | C owns it. A adds the `block_draft` rubric inside its anchor block. |
| `config/settings.yaml`, `config.py` | P00 (I), T14A.003 (A), and any lane that adds settings | Anchor blocks in both files (a lane's YAML keys + its `Settings` sub-model fields). Changing an existing key is a CR. |
| `config/routing.yaml`, `config/teams.yaml` | every lane that adds LLM tasks or teams | Anchor blocks. Temperatures follow R-LLM-06 and are reviewed at merge. |
| `config/personas.yaml` | P00 (I), T16.004 (D) | D owns it from W3. |
| `BUILD_LOG.md` | every phase close | Lanes **never** edit it. They write `sots-coord/buildlog/<lane>.md`, and I moves the lines in at the merge. |
| `blueprint/15_OPEN_ITEMS.md` | anyone with a question | Lanes **never** edit it. Questions go to `sots-coord/AUTHOR_QUESTIONS.md`, and I appends them to 15 §B at the merge. |
| `README.md` / `MUSE_START_HERE.md` | T21A.042 (D) | The author note is **already present** in both files, so T21A.042 is verify-only. D checks it and records the evidence. No edit. |
| `models/*` (existing modules) | any lane that needs a new field | Additive, optional fields only, through a **contract CR**. New model modules for a lane's own phase (for example `models/voice.py`) belong to that lane. |
| `storage/schema.sql` + `migrations/` | any lane that adds tables | See §4. |

## 3. Anchor blocks (created by Muse-I in Wave 0)

The format depends on the file's comment syntax. Blocks sit in the order I, A, B, C, D, with a blank line
between them, so git sees each lane's insertions as separate hunks:

```python
# >>> lane-A  (Muse-A only: append inside this block)
# <<< lane-A
```
```yaml
# >>> lane-A
# <<< lane-A
```
```sql
-- >>> lane-A
-- <<< lane-A
```

Files that get blocks: `cli.py` (registration), `config.py` (`Settings` fields), `config/settings.yaml`,
`config/routing.yaml`, `config/teams.yaml`, `config/grader.yaml`, `storage/schema.sql`,
`agents/failsafes/invariant_plugins.py`, `providers/context_pack.py` (TASK_PIECES), and, once D creates it
in W2, `eval/run_eval.py` (metric imports). Never edit, move, or reformat another lane's block. Never run a
formatter over a whole shared file; use `ruff check --fix` on your own paths only.

## 4. Database migrations

The runner applies every file it hasn't recorded yet (`storage/db.py:59`), so number ranges are safe.
The version is `wave × 100 + slot`:

| Slot | Owner |
|---|---|
| 00–19 | I and contracts (they apply first within a wave) |
| 20–39 | A |
| 40–59 | B |
| 60–79 | C |
| 80–99 | D |

Examples: A's first W1 migration is `120_a_supplement_docs.sql`, and D's first W3 migration is
`380_d_audience_tables.sql`. Wave 0 uses 003–099. The rules:

- Migrations are **additive**: CREATE TABLE/INDEX, or ADD COLUMN on a table your lane created. Altering a
  table you don't own requires a CR.
- Mirror every migration in `schema.sql`, inside your anchor block, in the same commit.
- Every migration needs a test that migrates an empty DB to head and round-trips its new model (F07 key included).

## 5. Tests and fixtures

- Unit tests: `tests/unit/test_<package>_<topic>.py`. The package prefix means lanes can never create
  files with the same basename.
- Integration tests: `tests/integration/test_<package>_<topic>.py`. Chaos tests: `tests/chaos/test_<package>_*.py`.
- Fixtures: `tests/fixtures/<package>/…`. Shared helpers: `tests/unit/helpers_<package>.py`.
- `tests/conftest.py` belongs to I. If you need a new shared fixture, send a CR, or put a helper in your own
  helpers module.
- Never edit, skip, `xfail`, or loosen a test your lane doesn't own. If another lane's test fails because of
  your change, send them a `BLOCKER` and fix your code or agree a CR.

## 6. TUI screen ownership (P22)

| Owner | Wave | Tasks |
|---|---|---|
| D (shell) | W2 | T22.001–T22.005, T22.050, T22.051 |
| D | W3 | T22.010 home, .012 runs, .015 psyche, .016 messages_voice, .017 shadow_goals, .021 settings, .030 chapter_board |
| A | W4 | T22.011 ingest, .020 profile + interview, .031 style_guide, .042 block_synthesis + foundation, .044 voice_lab |
| B | W4 | T22.013 claims + detail, .014 media, .018 expansion, .019 review_queue, .036 legal_chamber |
| C | W4 | T22.032 revision_review, .033 style_crosscheck, .037 proposal_desk, .038 below_bar, .039 grader_health, .041 export, .043 (grade_inspector, manuscript, revise-with-note widget) |
| D | W4 | T22.034 audience_lab, .035 persona_studio, .040 learning_inbox, .043 (reason, intent, Recheck button + reminder) |
| I | after M4 | T22.090 close; T22.052 goes to the author |
| C | W6 | T24.024 `tui/screens/master_audit.py` |

Screens live in `tui/screens/<name>.py` (one file per screen, so there are no conflicts). Keybindings are registered
through D's `tui/keys.py` API from each screen module. Nobody edits `keys.py` directly, except D.
