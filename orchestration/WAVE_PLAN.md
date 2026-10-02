# Wave plan

## 1. Real dependencies versus the written chain

The `Prerequisites:` lines in `tasks/` chain every phase to the one before it. The table below lists
the dependencies that are **code** dependencies: phase X imports, calls, or extends code that
phase Y creates. It comes from reading every task line and the file each task targets. Anything not
listed is covered by the P01 models (they already exist) plus fixtures.

| Phase | Hard code dependencies (must be merged first) | Soft (fixtures/models suffice) |
|---|---|---|
| P04 | P03 | — |
| P04A | P04 | — |
| P05, P06 | P04 (then P05) | — |
| P07 | P03 | P06 outputs (Unit model) |
| P08 | P07 | P11 ledger ("if available, else 1", T08.010) |
| P09 | P07, P08 | `classify/review_queue.py` (P06) → **deferred T09.008** |
| P10 | P03 | P06/P08/P09 outputs |
| P11 | P03 | messages via P04A (graceful mode T11.001) |
| P12 | P03 | P08–P11 outputs |
| P13 | P04–P12 (it wires every Act I stage) | — |
| P11A | P11 | `rewrite/style_guide.py` (P15) → **deferred T11A.032** |
| P13A | P04A, P08, P09, P14/P14M (graded proposals) | `acts/chapter_state.py` → **contract K3** |
| P14 | P03 | `eval/run_eval.py` (P13) → **deferred T14.032** |
| P14M | P14; `models/foundation.py` (tiers) → **contract K1** | audience/AIM data ("n/a" until built) |
| P14A | P14M, P04A, P13A, P11A | — |
| P15 | P14M, P11 (`local_similarity`) | `acts/chapter_state.py` → **K3**; `run_eval.py` → **K4** |
| P16 | P15, P14M | — |
| P17 | P07, P08, P14M, P15 (cross-check of legal edits) | P16 (order of acts only) |
| P18 | P07, P08, P14M | — |
| P19 | P14M, P18 | — |
| P20 | P14A, P15, P16, P17, P19 | — |
| P21 | P14, P16, P19, F18 replay | P20 (nominal only) |
| P21A | P14M, P04A | P21 (nominal only) |
| P22 | every phase whose screen it shows | — |
| P23 | everything | — |
| P24 | P23 | — |

## 2. Lanes

| Lane | Agent | Theme | Phases (in wave order) | Tasks |
|---|---|---|---|---|
| A | Muse-A | Foundation & Voice | P04, P04A, P05, P06 → P11A → P14A → TUI(A) | ~130 |
| B | Muse-B | Truth, Evidence & Law | P07, P08, P09 → P13A, P18 → P17 → TUI(B) | ~131 |
| C | Muse-C | Judgment & Craft | P14, P14M → P15 → P19 → P20 + TUI(C) → P24 | ~147 |
| D | Muse-D | Pipeline & Mind | P10, P11, P12 → P13 + TUI shell → P16 + TUI(D1) → P21, P21A + TUI(D2) → P23 code | ~160 |
| I | Muse-I | Integrator | Wave 0, merges M1–M4, W5 coordination, final close | — |

Why these groupings: each lane owns whole packages, so almost all of its edits stay inside
directories nobody else writes to (`OWNERSHIP_MAP.md`). The rewrite family (`rewrite/*`: P15, P20)
stays with one lane (C), because P20 edits the same files P15 creates. The fact-checking family
(research → verify → media → brief audit → discovery → legal authorities) stays with B, because it
shares fetchers, citation checks, and the VR rules. D owns the Act orchestration and the pipeline,
the psyche/narrative/shadow analysis that feeds it, and the TUI shell that displays it.

## 3. Waves

A wave ends when **every** lane in it has posted `READY-FOR-MERGE` for all of its phases and Muse-I
has finished the merge. A lane that finishes early does peer verification first (`BEST_PRACTICES.md
§5`). After that it may read the next wave's blueprint docs and write fixtures under its own
`tests/fixtures/<domain>/`. It **does not** check boxes or write code that depends on code that
hasn't been merged.

### Wave 0 (serial, Muse-I on `main`)
The Codex session that is currently building P03 finishes it (or stops). Muse-I then verifies P03
independently, fixes the debts in `PROJECT_AUDIT.md §3`, splits the hotspot files, creates the anchor
blocks, commits the baseline, and creates the worktrees. See `agents/MUSE_I_INTEGRATOR.md §2`.
**Exit:** tag `w0-baseline`, all gates green, `WAVE-START W1` broadcast.

### Wave 1
| Lane | Work | Contracts it must publish early |
|---|---|---|
| A | P04 → P04A → P05 → P06 | **K1** `models/foundation.py` (T04A.001), right after P04 closes. **K2** `AgentCard.foundation_pieces` (T04A.022) as a CR to C. |
| B | P07 → P08 → P09 (without T09.008) | — |
| C | P14 (without T14.032) → P14M | Consumes K1 before T14M.010. Reviews and acks K2 before T14M.043. |
| D | P10 → P11 → P12 | — |
**Merge M1 order:** A → B → D → C (foundation first, runtime-touching C last).

### Wave 2
| Lane | Work | Contracts |
|---|---|---|
| A | P11A (without T11A.032) | — |
| B | T09.008 (P09 then closes fully) → P13A → P18 | Consumes K3 before T13A.035 |
| C | T14.032 once K4 has landed (P14 then closes fully) → P15 (T15.074 after K4) | Consumes K3 before T15.071 |
| D | **K3** `acts/chapter_state.py` (T13.003) and **K4** `eval/run_eval.py` with its metric-registration hook (T13.011) as the first deliverables → the rest of P13 → TUI shell (T22.001–T22.005, T22.050, T22.051) | Publishes K3 and K4 |
**Merge M2 order:** D → A → C → B.

### Wave 3
| Lane | Work |
|---|---|
| A | T11A.032 (it now extends C's `rewrite/style_guide.py`; P11A then closes fully) → P14A |
| B | P17 |
| C | P19 |
| D | P16 → TUI(D1): T22.010, .012, .015, .016, .017, .021, .030 |
**Merge M3 order:** C → D → B → A.

### Wave 4
| Lane | Work |
|---|---|
| A | TUI(A): T22.011, .020, .031, .042, .044 |
| B | TUI(B): T22.013, .014, .018, .019, .036 |
| C | P20 → TUI(C): T22.032, .033, .037, .038, .039, .041, and the grade_inspector / manuscript / revise-with-note parts of .043 |
| D | P21 → P21A → TUI(D2): T22.034, .035, .040, and the reason / intent / Recheck button + reminder parts of .043 |
**Merge M4 (final) order:** C → D → B → A. Then Muse-I closes P22 (T22.090). T22.052 goes to the author.

### Wave 5: evaluation and live shakedown (on `main`, coordinated by Muse-I)
D implements T23.001–T23.003 in a short-lived branch. B writes the T23.004 gold-set instructions.
Muse-I walks the author through T23.005–T23.009, runs T23.010 (SotS fact-checks doc 21) and T23.011,
and writes T23.012. Lanes stay **on call**: a failure is routed to the owning lane as a `BLOCKER`
and fixed in a `fix/<lane>/<slug>` branch that goes through the normal merge procedure.

### Wave 6: Master Audit
C builds P24 on `main` in `lane/c/w6`. Muse-I merges it and closes the build (tag `build-complete`).

## 4. Deferred-by-plan tasks (needs AD-2)

| Task | Lane | Why it can't run in its own phase's wave | Lands in | Phase status meanwhile |
|---|---|---|---|---|
| T09.008 | B | It edits `classify/review_queue.py`, which A creates in P06 in the same wave | W2, B's first task | P09 "closed-with-deferral" |
| T14.032 | C | `eval/run_eval.py` doesn't exist until D's T13.011 (K4, W2) | W2, after K4 lands | P14 "closed-with-deferral" |
| T11A.032 | A | It rewrites `rewrite/style_guide.py`, which C creates in P15 (W2) | W3, A's first task | P11A "closed-with-deferral" |
| T15.074 | C | It needs `eval/run_eval.py` (K4) | W2, after K4 lands | normal (same wave) |

Rules: the deferral is listed in `sots-coord/DEFERRED.md`. The phase's `.090` close records
`closed-with-deferral (T…)` in the lane's build-log staging file. The task is picked up **first** when
its dependency lands. The phase counts as done only when the deferred task is checked and its `.090`
evidence is refreshed. A later phase in the same lane may start while a deferral is open, but only if
it doesn't need the deferred task's output.

## 5. Mid-wave contracts

A contract is a small interface-only change that another lane needs **during** the current wave.
It lands on `main` early through the contract fast-track (`COMMUNICATION_PROTOCOL.md §5`), and the
consuming lanes then merge `main` into their lane branch at the announced SYNC point.

| Id | Wave | Producer | Consumers | Content (interface only) |
|---|---|---|---|---|
| K1 | W1 | A | C (P14M), later B | `models/foundation.py`: EpistemicTier and the foundation models (T04A.001), with round-trip tests |
| K2 | W1 | A (CR to C, the W1 owner of `agents/cards.py`) | C | The `foundation_pieces` field on AgentCard + the doctor warning (T04A.022) |
| K3 | W2 | D | B (T13A.035 `acts/act0.py`), C (T15.071 `acts/act2.py`) | `acts/chapter_state.py`: the ChapterState lifecycle, `eligible_next_act`, blocked reasons (T13.003) |
| K4 | W2 | D | C (T14.032, T15.074), later B (T17.033) | `eval/run_eval.py`: the runner, plus a metric registry that lets each lane add its metric from its own module (T13.011) |

Doing a contract task early *inside* your own phase is allowed when that task doesn't depend on the
tasks before it in the same phase (true for T04A.001, T04A.022, T13.003, T13.011). Note the reordering
in the evidence entry.
