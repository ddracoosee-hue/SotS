# P00 — Skeleton

**Prerequisites:** none. **Blueprint refs:** 01, 02 §4–§6, 12 §1, 12 §3.1.
**Format:** `T<phase>.<nnn> | path | action | Done when`. Work top to bottom. Check the box when done.

## Project files
- [x] **T00.001** | `pyproject.toml` | Create a uv project `sots`, Python `>=3.12,<3.13`, with the dependencies from 02 §6 (runtime) and the dev group (pytest, pytest-asyncio, respx, ruff, pyright). Entry point `sots = "sots.cli:app"`. | `uv sync` succeeds on a clean clone.
- [x] **T00.002** | `pyproject.toml` | Add `[tool.ruff]` (line length 100, select E,F,I,B,UP,SIM,RUF), `[tool.pyright]` (basic, include src), `[tool.pytest.ini_options]` (asyncio_mode=auto; markers: live, chaos, tui). | `uv run ruff check`, `uv run pyright`, and `uv run pytest` run (0 tests is OK).
- [x] **T00.003** | `.gitignore` | Ignore `data/`, `profile/`, `supplements/`, `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `data/exports/`. | The file exists with every entry.
- [x] **T00.004** | `.env.example` | List every key name with an empty value: `MUSE_API_KEY`, `MUSE_BASE_URL`, `TAVILY_API_KEY`, `COURTLISTENER_TOKEN`, `GOOGLE_FACTCHECK_KEY`, `TMDB_API_KEY`, `CONTACT_EMAIL` (for API User-Agents). | Every key is present; no values.
- [x] **T00.005** | `BUILD_LOG.md` | Create it with the header `date | phase | status | note`. | The file exists.
- [x] **T00.006** | `README.md` | A short README: what SotS is, `uv sync`, `uv run sots init`, `uv run sots doctor`, a pointer to MUSE_START_HERE.md, and **the author note about Recheck & Reason** (the same wording as MUSE_START_HERE). | The file exists; ≤ 70 lines; the note is present.

## Folder tree
- [x] **T00.010** | `src/sots/**` | Create every package directory in 02 §4 (including agents/, grader/, proposals/, rewrite/, audience/, legal/, learning/, acts/, expand/), each with an `__init__.py`. | `python -c "import sots.agents, sots.legal, sots.audience"` works.
- [x] **T00.011** | `prompts/**` | Create every prompt subfolder from 02 §4 with a `.gitkeep`. | The folders exist.
- [x] **T00.012** | `tests/{unit,integration,tui,chaos,live,fixtures}` | Create the test folders + `conftest.py` with a `tmp_settings` fixture placeholder. | pytest discovers the folders.
- [x] **T00.013** | `eval/{gold,grader_gold,rewrite_gold,legal_gold,audience_gold,proposal_gold}` | Create them with a README in each describing its expected contents (copy from 14 §3 / §6.1). | The folders + READMEs exist.
- [x] **T00.014** | `config/agents/` | Create one subfolder per team in 16 §6. | The folders exist.

## Configuration
- [x] **T00.020** | `config/settings.yaml` | Write every setting referenced in the blueprint with its defaults: paths, providers (muse: all placeholders; local: base_url, model, num_ctx), chunk, context.budgets, budget, cache, concurrency, search, research, classify, expand, rewrite (pass_a.edit_budget 0.15, pass_b.edit_budget 0.35, pass_a.author_review false), languagetool, proposal_desk, discovery, audience, legal, privacy, safety. Comment each key with its blueprint section. | The YAML parses; every key has a comment with a doc reference.
- [x] **T00.021** | `config/routing.yaml` | Merge all routing blocks: 04 §3, 11 §6, 19 §7, 20 §8, 22 §8, plus grader.judge_a/judge_b/judge_c, proposals.*, fact_check specialist tasks. | The YAML parses; every task key is unique.
- [x] **T00.022** | `config/source_tiers.yaml` | Copy 06 §2 exactly. | It parses.
- [x] **T00.023** | `config/rubrics.yaml` | Copy 10 §2.1. | It parses; the weights sum to 1.0 (checked in a test).
- [x] **T00.024** | `config/system_goals.yaml` | Merge 10 §3, 11 §5, 06 §9.4, and 14 §6.2. | It parses.
- [x] **T00.025** | `config/safety.yaml` | Crisis resources (a generic international list + placeholders for the author's country) + `banned_labels` (a clinical disorder label list for R-PSY-02). | It parses; both keys are present.
- [x] **T00.026** | `config/teams.yaml` | Copy 16 §6. | It parses.
- [x] **T00.027** | `config/grader.yaml` | Encode the gates (17 §1) and all rubrics (17 §3.1–3.5, 22 §5 legal_argument) with ids, types, weights, floors, anchors, and hard checks. | It parses; a test asserts the weights sum to 1.0 per rubric.
- [x] **T00.028** | `config/formatting.yaml` | Copy 19 §1.3. | It parses.
- [x] **T00.029** | `config/personas.yaml` | Template set: 12 adult personas per 20 §4.1 (7 Gen Z adults 18–29, 4 Millennials 30–45, 1 Gen X 46–61), neutral ids, diverse per the coverage matrix; `reviewed: false`. | It parses; all ages ≥ 18.
- [x] **T00.030** | `config/audience/*` | Create thresholds.yaml, targets.yaml (20 §5.2), techniques.yaml (20 §7 list), and the starter word lists cliches.txt, dated_slang.txt, therapy_speak.txt, caricature_markers.txt (≥ 30 entries each). | The files exist and parse.
- [x] **T00.031** | `config/legal.yaml` | Jurisdictions (22 §3), the counsel roster L1–L8 with stance/method, exit thresholds (6/8, 3 cycles; delta 2/3). | It parses.

## Core modules
- [x] **T00.040** | `src/sots/errors.py` | Define: SotsError (base), ConfigError, ProviderNotConfiguredError, BudgetExceededError, ValidationFailedError, WriterDisabledError, GateFailedError, InvariantBrokenError, KillSwitchError, ToolNotAllowedError, LoopDetectedError, AdultsOnlyViolation. | Imports work; each has a docstring.
- [x] **T00.041** | `src/sots/config.py` | `load_settings(config_dir, env_file) -> Settings` (a frozen Pydantic model tree); env overrides for secrets; validates required keys. | Tests: valid load; a missing key → ConfigError; Settings is immutable.
- [x] **T00.042** | `src/sots/logging_setup.py` | JSON-lines logging to `data/logs/sots.jsonl` with run_id/agent context vars. | A test writes a log line and parses it back as JSON.
- [x] **T00.043** | `src/sots/writer/__init__.py` | `def draft(*a, **k): raise WriterDisabledError(...)`. | A test asserts it raises.

## CLI stubs
- [x] **T00.050** | `src/sots/cli.py` | A Typer app with every command and subcommand from 12 §1 and 12 §3.1. Unimplemented ones print "not yet implemented (phase Pxx)" and exit 1. `write` exits 2. | `sots --help` lists everything; a test covers the write exit code.
- [x] **T00.051** | `src/sots/cli.py` | Implement `sots init`: create the data dirs, an empty DB file placeholder, and copy the profile templates (author.md, book.md, messages.yaml, chapters/README.md, voice_corpus/README.md + manifest.yaml + the six register folders final/ drafts/ spoken/ casual/ pairs/ not_me/ (29)) if missing. | Running it twice changes nothing the second time (test).
- [x] **T00.052** | `profile_templates/` (package data) | Template files with headings matching the 03 §8 models and guidance comments. | The templates are copied by init.

## Phase close
- [x] **T00.090** | — | Run ruff, pyright, and pytest; fix everything. | All green.
- [x] **T00.091** | `BUILD_LOG.md` | Append the P00 line. | The line is present.
