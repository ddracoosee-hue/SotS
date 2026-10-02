# Next steps (2026-10-02)

Written for Muse-I to pick up. It updates `WAVE_PLAN.md` and `agents/MUSE_I_INTEGRATOR.md §2` to
match what actually happened after the plan was approved. Where this file and those two disagree,
this file wins **only for the points marked "changed"**. Everything else in them stands.

## 0. Where the project actually is

| Item | State |
|---|---|
| Git | One commit, `b68221a` "Baseline snapshot: blueprint + P00-P06 build (AD-3)". No tags, no worktrees. `profile/` and `data/` are gitignored and not in it. |
| P00–P06 + P04A | All boxes checked by a single solo session (P04 is 13/14; T04.006 is superseded by P04A). **Not independently verified.** BUILD_LOG lines exist for each. |
| OI-42 / OI-42b | Obsidian vault mirror built and logged. |
| P07 | **Partial and unlogged.** A session stopped at 2026-09-29 15:01 and nothing has changed since. Present: `research/{tiers,bm25,passages}.py`, `research/search/`, `research/fetchers/` (base, cache, web, courtlistener, openalex, crossref, google_factcheck, tmdb, openlibrary, musicbrainz, supplements, registry). Missing: `fetchers/wikipedia.py` at least. 0/24 boxes checked. |
| Gate | `pytest`: **549 passed, 1 failed**. The failure is `test_no_http_or_sdk_calls_outside_allowed_dirs` on `research/fetchers/base.py` (see decision N-2). `sots doctor` exits 0. |
| R-CODE-03 (AD-5) | Over 400 lines in `src/`: `storage/repo.py` 1,812 · `cli.py` 954 · `agents/base.py` 678 · `vault/notes.py` 403. |
| Coordination | `coord/` created in-repo in W0 (serial mode D-013; AD-6's blessed alt path). |

**What drifted from the plan:** Wave 0 was supposed to run right after P03. Instead the solo session
kept building P04 → P04A → P05 → P06, which is **all of Lane A's Wave 1 work**, and then started
Lane B's P07.

## 1. Author decisions (answered 2026-10-02)

**Answers:** N-1 **yes** (parallel). N-2 **yes**. N-3 **yes**. N-4 **check and finish** (Lane B verifies the
partial P07 code task by task and completes it). AQ-W0-1: **Muse starts from the beginning and checks
where and what was left off.** `MUSE_START_HERE.md` now says this (stale "Start at P00" line replaced).
In practice: Wave 0 step 3 re-verifies **every** finished phase from P00 up, not just P03–P06.

Original questions, kept for the record:

| # | Question | Recommendation |
|---|---|---|
| N-1 | Keep the parallel 4-lane plan (with the changes in §3), or switch to one agent building phases in order (§4)? | **Parallel**, as approved. |
| N-2 | The HTTP guard (T01.040) allows httpx only in `providers/` and `agents/tools/`, but blueprint 02 puts the fetchers (which use httpx) in `research/fetchers/`. Fix by adding `research/fetchers/` and `research/search/` to the guard's allowlist? | **Yes.** The folder tree is the more specific spec. Record it in `15_OPEN_ITEMS.md §B`. |
| N-3 | Move **P11** (message ledger, drift, flow, voice fingerprint) from Lane D to Lane A, so Lane A has Wave 1 work and P11A can follow right after it in Wave 2? | **Yes.** It fits Lane A ("Foundation & Voice") and shortens Lane D's chain, which is the longest. |
| N-4 | Leave the partial P07 code in place for Lane B to verify and finish, rather than deleting it? | **Yes.** It's committed, so nothing is lost if B decides to redo parts. |
| AQ-W0-1 | `MUSE_START_HERE.md` still says "Nothing is coded yet. Start at P00." It is yours (OI-04). Update the line, or let Muse-I add a one-line pointer to `BUILD_LOG.md`? | Your call. Until it changes, a new agent following the reading order would restart P00. |

## 2. Wave 0 (changed)

Follow `agents/MUSE_I_INTEGRATOR.md §2` with these changes. Log every step in
`coord/evidence/I/W0.md` (create `coord/` first via `scripts/setup_coord.ps1 -CoordRoot coord` if needed for logging).

1. **Quiet check.** Ask the author to confirm no Codex or other agent session is open on this repo.
   `src/` has been unchanged since 2026-09-29 15:01, so the 10-minute stability check should pass.
2. **Safety backup.** Unchanged: copy the project (with `profile/` and `data/`, without `.venv`) to
   `C:\Users\ddrac\sots-backup-20261002`. This matters most for `profile/`, which git doesn't hold.
3. **Verify P00 through P06 independently** *(changed: was P03 only; widened to P00 per AQ-W0-1)*.
   Start from P00 and work up. For every task in P00–P06 and P04A (plus OI-42/42b), run its "Done when" check. The boxes are already ticked by the session that built
   them, so un-tick any that fail and fix them. Specific checks that the audit flagged and that must
   be re-confirmed:
   - `tests/integration/test_demo_agent.py` and `test_failsafe_matrix.py` exist now. Confirm they
     actually exercise kill → resume and all of F01–F20.
   - `sots doctor` **exits 1** on a hard failure (plant a bad agent card). It exits 0 today on a
     clean setup, which is correct; the hard-failure path is what's unverified.
   - Walk the 13-item cross-cutting checklist in `tasks/00_TASK_INDEX.md` (0/13 checked).
   - Fix the BUILD_LOG P02 line ("64 tasks" → 20).
   - Run `sots init` in the main checkout and confirm `data/sots.db` is created.
4. **Debts, no behaviour change.** Unchanged procedure (before/after snapshot, identical test count,
   `--help` diffs clean). Current line counts are in §0. Add the 400-line guard test.
5. **The P07 guard failure.** Apply N-2 (allowlist edit + a §B note). Don't otherwise touch P07.
   Mark P07 in BUILD_LOG as `in progress (partial, unverified) — Lane B, W1`. Remove AQ-W0-1 from the
   W0 author questions; it's answered.
6. **Prepare for parallel work.** Unchanged (`.gitattributes`, invariant plugins, anchor blocks,
   `ENVIRONMENT_READY.md` header, AQ-W0-1, the `15_OPEN_ITEMS.md §B` notes). Also update
   `OWNERSHIP_MAP.md` for N-3: P11's files move from Lane D to Lane A.
7. **Full gate.** `ruff check .`, `pyright`, `pytest` twice, `sots doctor`, empty-DB migrate to head,
   `sots --help`. **All green, including the architecture test.**
8. **Baseline commit** *(changed: this is the second commit, not the first)*.
   `W0 baseline: P00–P06 verified, hotspot splits, orchestration pack`. Read `git status` in full
   first; `profile/`, `data/`, `.env`, `.venv`, and caches must be absent. Tag `w0-baseline` and `w1-start`.
9. **Coordination and branches** *(changed: serial mode D-013, no worktrees)*.
   `setup_coord.ps1 -CoordRoot coord`, `profile_manifest.ps1 -Manifest coord/profile_manifest.sha256`,
   `new_branches.ps1 -Wave 1`. The gate must be green before opening the wave.
10. **Open W1** with the revised table in §3. Seed `DECISIONS.md` with D-001…D-007 (AD-1…AD-7),
    D-008…D-012 for the author's answers to N-1…N-4 and AQ-W0-1, and D-013 (serial mode).

**Exit:** tag `w0-baseline`, gate green, `WAVE-START W1` broadcast.

## 3. Revised Wave 1 (changed)

Lane A's original W1 work (P04 → P04A → P05 → P06) is done and verified in Wave 0.

| Lane | Work | Notes |
|---|---|---|
| A | **P11** | Moved from D (N-3). K1 and K2 already exist on `main` (built in P04A), so A publishes nothing new; it confirms K1/K2 match `WAVE_PLAN.md §5` and posts that to `CONTRACTS.md`. |
| B | **P07 (finish)** → P08 → P09 (without T09.008) | Start P07 by verifying the existing code task by task against `P07_research_tools.md`, then build what's missing (`wikipedia.py`, citation check, etc.). |
| C | P14 (without T14.032) → P14M | Unchanged. K1 is already on `main`. |
| D | P10 → P12 | P11 moved to A. P12 only needs P08–P11 *outputs* (soft), so fixtures suffice. |

**Merge M1 order:** A → B → D → C (unchanged).

**Knock-on changes for later waves:**
- **Wave 2, Lane A:** P11A (without T11A.032) can start the moment A's own P11 is merged, so it
  no longer waits on D.
- **Wave 2, Lane D:** unchanged (K3, K4, rest of P13, TUI shell). P13 wires P11, so it consumes A's P11 from `main`.
- Waves 3–6 are unchanged.

## 4. If the author picks sequential instead (N-1 = no)

Do Wave 0 steps 1–8 only (skip worktrees and lanes), then build one phase at a time on `main`,
with a commit and BUILD_LOG line per phase, in this order (it respects every hard dependency in
`WAVE_PLAN.md §1`):

P07 (finish) → P08 → P09 → P10 → P11 → P12 → P13 → P14 → P14M → P11A → P13A → P14A → P15 → P16 →
P17 → P18 → P19 → P20 → P21 → P21A → P22 → P23 → P24.

## 5. Author track (runs alongside, blocks nothing)

These improve what SotS actually writes far more than any build-side change:

| Item | What | Needed by |
|---|---|---|
| OI-40 | Raw dictation or an earlier draft of Chapter 1 → `profile/voice_corpus/pairs/`. The single most valuable voice input. | P11A (W2), P14A (W3) |
| OI-41 | Any other writing → `profile/voice_corpus/` (final, drafts, spoken, casual, not-me). | P11A (W2) |
| OI-02 | Review `profile/CORE_MESSAGES_REVIEW.md`. | P11 message ledger (W1) |
| OI-04 | Muse operating instructions in `MUSE_START_HERE.md`. | any time |
| OI-15 | Approve the generated Style Guide. | Before Pass A *runs* (after P15 is built, W2) |
