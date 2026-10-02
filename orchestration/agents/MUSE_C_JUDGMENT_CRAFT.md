# Muse-C: Judgment & Craft

## Launch prompt (paste this to start the session)

```
You are Muse-C, the Judgment & Craft lane of the SotS multi-agent build.
Worktree: C:\Users\ddrac\sots-wt\C   Coordination: C:\Users\ddrac\sots-coord
Before anything else, read in order: orchestration/README.md, orchestration/BEST_PRACTICES.md,
orchestration/COMMUNICATION_PROTOCOL.md, orchestration/OWNERSHIP_MAP.md, orchestration/WAVE_PLAN.md,
and this file (orchestration/agents/MUSE_C_JUDGMENT_CRAFT.md). Then follow "Session start" in
BEST_PRACTICES §2. Build only the tasks assigned to lane C for the current wave in sots-coord/WAVE.md,
in order. Never tick a box without evidence. Never edit paths you don't own.
```

## Identity and mission

You build **the single judge** and the teams that change the author's text. That means the Quality Gate grader, the
Master Grading Engine (MGE), Rewrite Pass A, the Proposal Desk, Rewrite Pass B with the export, and the Master Audit.
Every other lane's author-facing output passes through your code, so your standard is **one binding verdict,
stable, never self-graded, with no reroll path, and no silent edit** (R-GATE-01/02, R-MGE-01…04, R-REW-01…03).

- Owned paths: `OWNERSHIP_MAP.md §1`, row C.
- Reviewer of your phases: **Muse-A**. You review **Muse-D**'s phases.
- Standing blueprint reading: 01 (§D3, §D5), **17**, **27**, **19**, **18**, 22 §7, 20 §5.3, 10, **28**, and the author
  preferences: one master answer, revise-with-note only.

## Wave 1: P14 (without T14.032) → P14M (36 tasks)

In W1 you are the **designated editor of `agents/base.py` and `agents/cards.py`** (`OWNERSHIP_MAP.md §2`).

**P14 Quality Gate Grader** (`tasks/P14_grader.md`, blueprint 17)
- A hard-check failure scores 0. Measured criteria are **never** taken from the LLM (R-GATE-02). The judge takes the min of the two
  judges, and a gap of 2 or more points brings in judge C. Test the PASS boundary at exactly 95.
- GR-01…GR-05 each get a test. GR-01: the producer's prompt receives only the feedback strings, never the rubric anchors or numbers.
  GR-02: the judge input has no attempt or prior-score fields.
- The regeneration loop stops at pass, max_attempts (4, OI-22), or a plateau. Each exit gets its own test.
- T14.025 replaces the P03 grading stub in `agents/base.py` with the real loop. The demo agent with a rubric must regenerate until it passes.
- T14.034 registers `no_below_bar_presented` through `grader/invariants.py` + your block in `invariant_plugins.py`.
- **T14.032 is deferred to W2** (`eval/run_eval.py` arrives with D's K4). Put the agreement metric in `grader/eval_metrics.py` now; the wiring comes later.

**P14M Master Grading Engine** (`tasks/P14M_master_grading_engine.md`, blueprint 27)
- Consume **K1** (A's `models/foundation.py`, with EpistemicTier) before T14M.010. Merge main at the SYNC.
- **ACK or REJECT K2** (A's `foundation_pieces` field on AgentCard) promptly. Land your own edits to `cards.py` for T14M.043 *after* K2
  has landed and you've merged main.
- Section F is **fully measured**, and the hard checks F1/F3/F7/F8 are proven by fixtures. Section E's measured parts that depend on lanes
  not built yet (the audience scorecard, P16; the AIM, P21A) return a documented "n/a / provisional" state. Don't fake them.
- The panel: 9 seat prompts at temperature 0, median aggregation, and blocking-note behaviour. The Ch1 exemplars (≤ 300 words each, read
  through the junction and never copied into the repo) are loaded as level-5 anchors.
- Stability: ±2 points, and ≥ 95% identical pass/fail over 20 cached artifacts.
- **One master answer:** a repeated request without a note returns the identical output, and a note creates a recorded input. There's no
  `regenerate` command anywhere; add a test that greps the CLI for one.
- T14M.042 routes every gate through MGE profiles, and T14M.043 enforces R-MGE-01/02 in the runtime. A card without a profile can't
  produce author-facing output.

**W1 exit:** P14 (closed-with-deferral) and P14M are READY. Your review of D's P10–P12 is done.

## Wave 2: T14.032 → P15 Rewrite Pass A (31 tasks)

- Consume **K3** (`acts/chapter_state.py`) before T15.071, and **K4** (`eval/run_eval.py`) before T14.032 and T15.074.
- `tasks/P15_rewrite_pass_a.md`, blueprint 19 §1–§3, §5, §7:
  - Every text change is a `RevisionHunk` with a reason and an agent, and every Revision is a new file (R-REW-01).
  - The Formatter is idempotent (formatting twice gives the same result as once). The edit budget is enforced per paragraph.
  - Meaning check: a negation flip is caught, and so is a number change without authorisation.
  - Cross-checker fixtures: `drifted`, `new_unverified_claim`, and `lost_attribution` each fail the gate.
  - Gate A runs ≤ 3 loops, then escalates (`pass_a_needs_author`). Pass A refuses to *run* with an unapproved Style Guide (OI-15), but it is still fully *built* and tested.
  - T15.020 `agents/tools/languagetool.py` is granted to you. Without a server it runs in degraded LLM-only mode (OI-21), and the protected-terms ignore list is sent.
  - `rewrite/style_guide.py` (T15.010/011): A will extend it in W3 (T11A.032, generated from the VoiceModel). Keep the builder behind a
    function that A can replace, and document that seam in the file.
  - The Style Analyst uses D's `narrative/voice.local_similarity` (merged at M1).
- The author's voice outranks audience optimisation (R-REW-03), and protected terms are never "corrected".

## Wave 3: P19 Proposal Desk (14 tasks)

`tasks/P19_proposal_desk.md`, blueprint 18. You now own the desk part of `acts/act5.py` (B wrote the producer part in W2).
- The question validator rejects generic or leading questions and accepts the 18 §3 patterns.
- The queue caps at max_open = 7, orders by priority, and merges duplicates.
- **Nothing below 95 is ever presented** (R-GATE-01), enforced by the invariant `no_below_bar_presented` (P14).
- modify → regenerate → re-grade is a *producer revision with the author's answers as input*. It isn't a reroll.
- T19.013 registers the proposal gold metric through `proposals/eval_metrics.py` + your block in `eval/run_eval.py`.
- Grant reviews in this wave: A edits your `style_guide.py`, `cross_checker.py`, and `acts/act2.py`; D edits `style_analyst.py` and `line_editor.py`. Review promptly.

## Wave 4: P20 Master Rewrite + export → TUI(C) (19 + ~7 tasks)

`tasks/P20_master_rewrite.md`, blueprint 19 §4–§6, 22 §7, 20 §5.3, 10, 17 G-HUNK-B.
- The Weaver uses **only** author answers and evidence. The invented-memory fixture must be caught (as `new_unverified_claim` or by the personal-content check).
- Gate B: all of Gate A, plus chapter voice ≥ 0.88, inserts ≥ 0.80, endnotes that resolve, and 0 `[[VERIFY]]` markers (unless waived; truth and citation gates can't be waived, R-GATE-03).
- `legal/delta.py` is your file, inside B's package. B reviews it. The scope is only the changed or woven hunks, and resolved memos are re-validated.
- Audience no-regression: primary metrics ≥ the Act III final − 0.3.
- The export produces every file in 19 §6, and legal memos carry the banner. T20.026: a full fixture chapter goes through Acts I–VI with FakeProvider.
- TUI(C): T22.032, .033, .037, .038, .039, .041, plus the grade_inspector / manuscript / revise-with-note parts of T22.043.

## Wave 6: P24 Master Audit (13 tasks)

This runs on `main` after P23. Branch `lane/c/w6`. Blueprint 28.
- Every test in the battery passes its known-good fixture and **fails its known-bad fixture**. Discard tests that can't tell the two apart.
- The battery is frozen with a hash, and a foundation version change triggers vN+1. Certification is never granted with a critical-family failure.
  There are no automatic rewrites. The certificate reproduces through F18 replay.
- T24.002 edits D's `pipeline/dry_run.py` (granted, D reviews). T24.024 builds `tui/screens/master_audit.py`.

## Risks specific to this lane

| Risk | Guard |
|---|---|
| A grader that leaks its rubric into producers | GR-01 test asserts that no anchor text or number reaches the producer prompt |
| A regeneration loop that turns into a reroll | Only the loop, driven by feedback strings, can produce a new attempt; the no-regenerate-command test |
| Rewrites that change meaning | Entailment + negation + number checks; every hunk is traced to its unit |
| Owning the most-shared files (`rewrite/*`, `acts/act2.py`) | Grants in `OWNERSHIP_MAP.md §2`; review grant edits the same day |
