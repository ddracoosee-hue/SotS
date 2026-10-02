# Project audit: 2026-09-29, ~12:10 MDT

Method: I read the top-level docs, the build log, all 31 task files, the rules (01), the build
phases (13), the open items (15), the architecture (02 §2A, §2, §5–§7), and the storage, CLI,
and agent source. I also ran the verification commands myself. Every claim below says how I
verified it: **[ran]** means I executed a command today, **[read]** means I inspected files,
and **[claimed]** means the claim comes only from a log or doc.

## 1. Headline

| Area | State |
|---|---|
| Blueprint + profile foundation | Complete (29 spec files, 12 briefs, anchors, architecture, Ch1 author-final). **[read]** |
| Phases done | **P00, P01, P02**: 81 of 620 task boxes checked. **[read]** |
| Phase in progress | **P03 (agent runtime)**: 0 of 45 boxes checked, but most modules exist. An active Codex session was writing `agents/base.py` during the survey (13.5 KB → 27.7 KB between 12:10 and 12:11:42). **[read]** |
| Phases not started | P04 → P24: 539 boxes (P25 is locked). **[read]** |
| Tests | `pytest`: **368 passed** in 23.6 s (live tests deselected). **[ran]** |
| Types | `pyright`: **0 errors**. **[ran]** |
| Lint | `ruff check .`: **15 errors**, all F401 unused imports in the in-progress `agents/base.py`. **[ran]** |
| Git | **No commits.** Every file is untracked. There is no remote, no worktree, and no baseline. **[ran]** |

## 2. Completed and verified

| Item | Evidence |
|---|---|
| Environment: Python 3.12.10, uv, a locked `.venv`, and the approved dependencies only | `uv run` works; `pyproject.toml` lists exactly the 02 §6 packages. **[ran][read]** |
| P00 skeleton: 32/32 boxes; `sots --help` lists every command; `sots write` exits 2 | **[ran]**: `write exit=2`, and the help output lists 29 commands and sub-apps |
| P01 models + storage: 29/29 boxes; 23 model modules; `schema.sql` + migrations 001–002; typed repo; arch lint guard | The storage and model tests pass. **[ran]** |
| P02 providers: 20/20 boxes; fake/local/muse adapters, router, cache, budget, call log, context packs | The provider tests pass. **[ran]** |
| OI-42 / OI-42b Obsidian vault (author-approved) | `data/vault/` is populated; the vault tests pass. **[ran][read]** |
| P03 failsafes F01–F20: every module exists, and each is referenced by name in `test_failsafes1/2.py` (36 tests) | **[read]** |
| P03 tools: every module in `agents/tools/` exists, with 35 tests | **[read]** |

## 3. Unverified, incomplete, or out of spec

These are ordered by impact. Muse-I clears items 1–9 in Wave 0.

1. **No git history at all.** Nothing is committed, so a bad edit can't be recovered and worktrees are
   impossible. `profile/` and `data/` are gitignored by design (R-DATA-04, OI-33), so the author's
   foundation has **no version control and no backup** beyond the FoundationChange records. → Wave 0
   baseline commit (AD-3), plus the profile sha256 manifest.
2. **P03 is mid-build and unverified.** No box is checked, and these are missing:
   - No test references `load_cards`, `BaseAgent`, `EventBus`, or `register_agent` (T03.001/002/010–016/070 are unverified).
   - `tests/integration/` is empty: T03.080 (the demo agent kill/resume) and T03.081 (the failsafe matrix) don't exist yet.
   - `sots doctor` prints "not yet implemented (phase P03)" and **exits 0**. T03.056 requires exit 1 on hard failure.
   - `config/agents/_demo/demo_agent.yaml` exists, but its load test is unverified.
3. **Ruff is not clean** (15 × F401 in `agents/base.py`). This is probably transient while the file is being written.
4. **R-CODE-03 violations (no file > 400 lines)**, even though P00/P01/P02 were logged green:
   `storage/repo.py` **1,793**, `agents/base.py` **678**, `cli.py` **641**, `vault/notes.py` **403**.
   Also over the limit: 5 test files (`test_storage.py` 1,072, `test_provider_services.py` 615,
   `test_vault.py` 537, `test_providers.py` 485, `test_failsafes1.py` 415) and both SQL files (884/881).
   AD-5 (answered 2026-09-29): the limit covers `src/**/*.py` only, so the test and SQL files are exempt. The P00–P02 closes therefore did not fully satisfy
   the rules. No automated guard for the limit exists yet.
5. **The cross-cutting checklist** in `tasks/00_TASK_INDEX.md` has 0 of 13 items checked. It was never
   verified at a phase close.
6. **Stale onboarding docs.** `MUSE_START_HERE.md` ("Nothing is coded yet. Start at P00.") and
   `ENVIRONMENT_READY.md` ("Do not assume T00.001/T00.002 or P00 are complete") contradict the build log.
   A new agent that reads them in the prescribed order would restart P00. The author owns
   `MUSE_START_HERE.md` (OI-04), so this pack does not edit it. Muse-I raises it as an author question.
7. **A build-log inconsistency.** The P02 line says "(64 tasks)", but P02 has 20 tasks. The phase-close
   evidence isn't recorded anywhere except that one line.
8. **`sots init` was not re-verified.** `data/sots.db` does not exist in the main checkout, so `init` has not been
   run there since P00. The tests cover it. **[claimed via tests]**
9. **The migration runner applies by set difference** (`storage/db.py:59`): it records each version and skips
   applied ones. This makes per-lane number ranges safe. But `schema.sql` must mirror every migration, and
   it is one 884-line file, so it is a merge hotspot. → anchor blocks (`OWNERSHIP_MAP.md §3`).

## 4. External and live services (these don't block offline work)

| Service | State | Owner |
|---|---|---|
| Muse API | Unknown endpoint/auth (OI-03); the router falls back to local | author |
| Ollama | 0.32.13 with 18 models incl. qwen3:14b (per ENVIRONMENT_READY, **[claimed]**) | OI-05 |
| SearXNG / LanguageTool | Not installed; the Docker engine isn't running | OI-07 / OI-21 |
| API keys | None (OI-08); key-gated fetchers must disable cleanly | author |
| Codex runner | ENVIRONMENT_READY reports pipe timeouts in the Codex sandbox runner | tooling |

## 5. Waiting on the author (from 15 §A, still open)

OI-02 (core messages review), OI-03, OI-04 (the Muse operating instructions; this pack is a candidate
input), OI-05–09, OI-11–25 as listed, OI-28–31, OI-33, OI-40/41 (voice material). None of these blocks a
phase. Each has a default. The **[author verifies]** tasks are T22.052 and T23.005–T23.009.

## 6. Structural facts that shape the plan

- The phase prerequisites in `tasks/` form one **strict chain** (P03→P04→…→P24). The real code
  dependencies are much looser (`WAVE_PLAN.md §1`). Running in parallel needs author decision AD-1.
- A script cross-referenced every task's target file against its lane. **27 files are touched by
  tasks from more than one lane.** The worst are `cli.py` (25 tasks, all lanes), `failsafes/f20_invariants.py`
  (9 tasks, all lanes), `eval/run_eval.py` (7), `agents/base.py` + `agents/cards.py` (P03, P04A, P14, P14M),
  `rewrite/*` (P11A, P14A, P15, P20), and `acts/act2.py` (P14A, P15). The full table and each file's rule
  are in `OWNERSHIP_MAP.md §2`.
- `profile/` is gitignored, so **a fresh worktree has no `profile/`**. Foundation-dependent code and tests
  would fail there. → the junction (AD-7).
