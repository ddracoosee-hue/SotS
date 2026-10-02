# SotS multi-agent build: orchestration pack

Written 2026-09-29 from a full survey of the repository (see `PROJECT_AUDIT.md`).
It describes how **four Muse lane agents** and **one Muse Integrator** build the remaining
~540 tasks in parallel, in separate git worktrees, without breaking the blueprint's rules.

> **Status: APPROVED by the author 2026-09-29 (AD-1…AD-7 all yes; AD-5 = source files only).**
> Wave 0 may start once the in-progress P03 session has finished or been stopped.
> The blueprint (`blueprint/`) and `MUSE_START_HERE.md` are unchanged. This pack sits
> beside them, and the author can point the Muse operating instructions (OI-04) at it.

## 1. Files in this pack

| File | Read it when | Contents |
|---|---|---|
| `README.md` | first | Overview, launch sequence, author decisions |
| `PROJECT_AUDIT.md` | before Wave 0 | What is done, what is verified, what is unverified or out of spec |
| `WAVE_PLAN.md` | before any wave | Dependency analysis, lane assignments per wave, deferred tasks, mid-wave contracts, merge order |
| `OWNERSHIP_MAP.md` | before every edit outside your own package | Who owns which path, the hotspot files, anchor blocks, migration number ranges, the TUI screen split |
| `COMMUNICATION_PROTOCOL.md` | at every session start | The coordination folder, message types, change requests (CRs), installs, sync points |
| `BEST_PRACTICES.md` | at every session start | Accuracy discipline, the definition of done, evidence, peer verification, conflict prevention |
| `agents/MUSE_A_FOUNDATION_VOICE.md` | Muse-A | Lane plan: foundation, ingest, segment, classify, Voice Lab, Block Synthesis |
| `agents/MUSE_B_TRUTH_LAW.md` | Muse-B | Lane plan: research tools, the fact-check team, media, Act 0 brief audit, discovery/expansion, Legal Chamber |
| `agents/MUSE_C_JUDGMENT_CRAFT.md` | Muse-C | Lane plan: grader, MGE, Pass A, Proposal Desk, Pass B + export, Master Audit |
| `agents/MUSE_D_PIPELINE_MIND.md` | Muse-D | Lane plan: psyche, narrative, shadow, Act I orchestration, Audience Lab, TUI shell, learning, Recheck & Reason |
| `agents/MUSE_I_INTEGRATOR.md` | Muse-I | Wave 0 steward work, the merge procedure, final integration, P23 coordination |
| `scripts/*.ps1` | Wave 0 | Coordination folder setup, worktree creation, profile manifest, lane verification |

## 2. The shape of the build

```
            ┌───────────── Wave 0 (serial, main) ─────────────┐
            │ current Muse finishes P03 → Muse-I verifies it, │
            │ fixes debts, splits hotspot files, first commit │
            └───────────────────────┬─────────────────────────┘
                                    │ tag w0-baseline
      ┌──────────────┬──────────────┼──────────────┬──────────────┐
  Muse-A          Muse-B         Muse-C          Muse-D
  (worktree)      (worktree)     (worktree)      (worktree)
  W1 P04 P04A     W1 P07 P08     W1 P14 P14M     W1 P10 P11
     P05 P06         P09                            P12
      └──────────────┴───── Merge M1 by Muse-I ─────┴──────────────┘
  W2 P11A         W2 P13A P18    W2 P15          W2 P13 + TUI shell
      └──────────────┴───── Merge M2 by Muse-I ─────┴──────────────┘
  W3 P14A         W3 P17         W3 P19          W3 P16 + screens
      └──────────────┴───── Merge M3 by Muse-I ─────┴──────────────┘
  W4 TUI screens  W4 TUI screens W4 P20 + screens W4 P21 P21A + screens
      └──────────────┴───── Merge M4 (final) ───────┴──────────────┘
                                    │
            W5  P23 evaluation + live shakedown (author verifies), coordinated by Muse-I
            W6  P24 Master Audit (Muse-C) → Muse-I final close
```

Every lane builds its own phases **in blueprint order**. A lane never starts work that needs
another lane's code until that code has been merged to `main` by Muse-I (or landed early
as a **contract**, see `COMMUNICATION_PROTOCOL.md §5`). The Integrator merges only work
that has fully passed, and it merges at the end of every wave, not just at the end of the
build. With four long-lived branches and no intermediate merges, the final merge would hit
conflicts that nobody could resolve reliably. The dependency analysis in `WAVE_PLAN.md`
shows that later waves need earlier waves' code merged anyway.

## 3. Launch sequence

1. **Do not start any lane while P03 is in progress.** On 2026-09-29 at 12:11, a Codex session
   was actively writing `src/sots/agents/base.py`. Let it finish P03, or stop it cleanly.
2. The author answers the decisions in §4.
3. Start **Muse-I** with `agents/MUSE_I_INTEGRATOR.md` → Wave 0. Muse-I ends Wave 0 by
   tagging `w0-baseline`, running `scripts/setup_coord.ps1` and `scripts/new_worktrees.ps1`,
   and broadcasting `WAVE-START W1`.
4. Start the four lane agents, each in its own worktree folder with its own plan file. Paste
   the "Launch prompt" block from the top of that file.
5. Muse-I watches the merge queue, runs M1–M4, and broadcasts each next wave.
6. After M4, run W5 (P23) and then W6 (P24).

The plan works whether the agents run as Codex sessions or Claude Code sessions. The
coordination folder is plain files, so any agent that can read and write files can take
part. Claude Code sessions can also nudge each other with `SendMessage`, but the files
remain the source of truth.

## 4. Author decisions (answered 2026-09-29)

**Answers:** AD-1 yes · AD-2 yes · AD-3 yes · AD-4 yes · AD-5 **`src/**/*.py` only** (tests and `.sql` are exempt) ·
AD-6 yes · AD-7 yes. Muse-I records these as D-001…D-007 in `sots-coord/DECISIONS.md` in Wave 0 and appends
them to `blueprint/15_OPEN_ITEMS.md §B`.

| # | Decision | Recommendation | If "no" |
|---|---|---|---|
| AD-1 | Allow **parallel lanes** as an explicit exception to R-SCOPE-03 ("build phases strictly in order"). Each lane keeps strict order *inside* the lane, and cross-lane dependencies are gated by merges. | **Yes.** The real code dependencies (`WAVE_PLAN.md §1`) allow it. | One Muse builds P03→P24 serially. The rest of this pack still applies as best practice. |
| AD-2 | Allow **deferred-by-plan tasks** (`WAVE_PLAN.md §4`, 4 tasks). A phase may close as "closed-with-deferral" when a single task is waiting on another lane's file, and the phase closes fully when that task lands. | **Yes.** | Those phases move one wave later, and the build takes one extra wave. |
| AD-3 | Make the **first git commit** (the baseline) of everything except `profile/` and `data/`, which stay gitignored per R-DATA-04. Worktrees cannot exist without a commit. | **Yes.** | No worktrees are possible, so the parallel build cannot run. |
| AD-4 | Wave 0 **splits the files over 400 lines** (`storage/repo.py` 1,793, `cli.py` 641, `agents/base.py` 678, `vault/notes.py` 403) with no behaviour change. This enforces R-CODE-03 and removes the worst merge hotspots. `storage/repo.py` becomes the package `storage/repo/` (R-CODE-03 overrides the wording of 02 §5; Muse-I logs this in 15 §B). | **Yes.** | The files stay over the limit (a standing R-CODE-03 violation) and every lane conflicts on them. |
| AD-5 | Does R-CODE-03's 400-line limit apply to **test files and `.sql` files**? (5 test files and both SQL files exceed it.) | Apply it to `src/**/*.py` only, and log the answer in 15 §A. | Wave 0 also splits the tests and the SQL files. |
| AD-6 | Put the coordination folder at `C:\Users\ddrac\sots-coord\`, with its own git repo for history, outside every worktree. | **Yes.** | Pick another path; the scripts take `-CoordRoot`. |
| AD-7 | Each worktree reaches `profile/` through a **directory junction** to the main checkout's `profile/`. It is read-only by rule (R-FOUND-02) and checked by a sha256 manifest at every merge. | **Yes.** | Each worktree gets a copy, and the copies can drift. |

## 5. What "done" means for the whole build

- Every task box in `tasks/` is checked, and every box has an evidence entry (`BEST_PRACTICES.md §3`).
- `main` at tag `m4-final` is green: ruff, pyright, pytest (twice, to catch flakiness), `sots doctor`,
  `sots eval` with no release-blocker regression, and the profile manifest unchanged.
- The cross-cutting checklist in `tasks/00_TASK_INDEX.md` has been verified at every merge.
- P23's **[author verifies]** steps have been completed with the author, and P24 has been built and run.
- P25 has not been started. It is **LOCKED**.
