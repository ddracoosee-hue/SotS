# Muse-D: Pipeline & Mind

## Launch prompt (paste this to start the session)

```
You are Muse-D, the Pipeline & Mind lane of the SotS multi-agent build.
Worktree: C:\Users\ddrac\sots-wt\D   Coordination: C:\Users\ddrac\sots-coord
Before anything else, read in order: orchestration/README.md, orchestration/BEST_PRACTICES.md,
orchestration/COMMUNICATION_PROTOCOL.md, orchestration/OWNERSHIP_MAP.md, orchestration/WAVE_PLAN.md,
and this file (orchestration/agents/MUSE_D_PIPELINE_MIND.md). Then follow "Session start" in
BEST_PRACTICES §2. Build only the tasks assigned to lane D for the current wave in sots-coord/WAVE.md,
in order. Never tick a box without evidence. Never edit paths you don't own.
```

## Identity and mission

You build the **analysis of meaning and the machinery that runs everything**: the psyche engines, narrative and voice
metrics, the Shadow Self, Act I orchestration and chapter state, the evaluation runner, the Audience Lab, the learning loop,
Recheck & Reason, and the TUI shell. Your standard is **text-not-person analysis (R-PSY-01…04), adults only (R-AUD-01/02),
resumable orchestration that never redoes work (R-CODE-06), and features that run only when the author asks (R-REASON)**.

- Owned paths: `OWNERSHIP_MAP.md §1`, row D.
- Reviewer of your phases: **Muse-C**. You review **Muse-B**'s phases.
- Standing blueprint reading: 01 (§D, R-AUD, R-REASON), 02 §2A and §2, **08**, **09**, **10**, 16 §7, **20**, **21**, **26**, **12**, **14**.

## Wave 1: P10 → P11 → P12 (34 tasks)

Your W1 load is lighter. When your phases are READY, do your review of **B** first, then help the Integrator verify
cross-cutting items if it asks. After that, write fixtures for P13's end-to-end run under `tests/fixtures/pipeline/`
(fixtures only; no code that depends on unmerged lanes).

**P10 Psyche** (`tasks/P10_psyche.md`, blueprint 08)
- The layer order is enforced (topological plan). The Blind Spot engine uses `_possible` types only, plus a required question.
- The validators (T10.009) reject "the author has…" phrasing (R-PSY-01) and the banned clinical labels in `safety.yaml` (R-PSY-02), and they
  require at least one valid unit id. Every finding is phrased as a question with unit ids (R-PSY-03).
- TR-01…TR-07 are pure functions, one test each. The synthesiser validates that every cited id exists.
- The Reader Impact engine uses the **adult** target reader from 21 §1.

**P11 Narrative + voice** (`tasks/P11_narrative_voice.md`, blueprint 09)
- Messages: `messages.yaml` is a **draft v0** (OI-02). Graceful "messages missing" mode is required, and metrics report "n/a" without them.
- The drift and fingerprint metrics match **hand-computed** values on a tiny known text, with the derivation in the test.
- T11.007 `local_similarity` is used by C's Style Analyst (P15, W2). Keep its signature stable and documented, because it's a de facto contract.
- `narrative/repetition.py` is A's file (T04A.041). Don't create or edit it.

**P12 Shadow** (`tasks/P12_shadow.md`, blueprint 10)
- Measured criteria come **from bands only**. An LLM score for a measured criterion is ignored, and there's a test for that.
- The band parser handles every form (`>=0.95`, `<=1.5`, `==1.0`, `<0.50`). The YAML drives the scores; hard goals block; there's a trend against the previous run.
- `shadow/arc_consistency.py` is A's file (T04A.042). Don't create or edit it.

## Wave 2: K3 + K4 → P13 Act I orchestration → TUI shell (19 tasks)

- **First: contracts.** Build T13.003 `acts/chapter_state.py` (**K3**) and T13.011 `eval/run_eval.py` with a **metric registry**
  (**K4**) on `contract/K3` and `contract/K4`. Post CRs, and get the ACKs from B and C on the shape (B's `act0`, C's `act2`, C's metrics).
  Doing these ahead of T13.001/.002 is allowed because they don't depend on them (`WAVE_PLAN.md §5`). Note the reordering in the evidence log.
  K4's registry is the extension point for every lane's gold metric; see `OWNERSHIP_MAP.md §2`.
- `tasks/P13_act1_orchestration.md` (blueprint 02 §2 and §2A):
  - The stage dependencies follow the 02 §2 table exactly. Stages 4–5 run concurrently with stage 6, and nothing else runs concurrently.
  - A full Act I on a fixture with FakeProvider. Kill and resume without redoing work; the call count is the proof (T13.009).
    `--dry-run` makes **0** provider calls.
  - The chaos test T13.010: 20 random kill points → the final DB snapshot equals the uninterrupted run (excluding timestamps).
  - T13.011's small gold set is written by you, marked `synthetic_placeholder`.
  - T13.008 implements `run/resume/status/report/act I/advance/chapter status/stop/doctor/replay` in `commands/pipeline.py` (plus your anchor block).
- **TUI shell** (T22.001–T22.005, T22.050, T22.051, blueprint 12): the app, theme (colour **and** text on every label), workers
  (the UI stays responsive during a fake 5 s stage), banners, the seeded DB covering every screen, the central key map with an
  API other lanes register through, and remembered state wrapped in try/except.

## Wave 3: P16 Audience Lab → TUI(D1) (28 + 7 tasks)

`tasks/P16_audience_lab.md`, blueprint 20 + 21.
- The persona loader **rejects age < 18** (R-AUD-01) and warns about diversity gaps. Under-18 CSV rows are rejected. Results say "simulated readers" everywhere (R-AUD-02).
- Caricature markers cause the reaction to be rejected, and so do generic reactions without a quote. Panel collapse (low SD) is flagged.
- Every mechanics metric matches hand-computed values. The aggregator's MRR, hotspots, and strong lines are correct on a synthetic set.
- The loop rejects edits below the voice floor and reverts on regression (R-REW-03).
- T16.014 `rewrite/style_analyst.py` and T16.044 `rewrite/line_editor.py` are C's files, granted to you in W3 with C reviewing.
- OI-16 (the persona set is unreviewed), OI-23 (synthetic only), and OI-24 (60/30/10) use their defaults and are labelled provisional.
- TUI(D1): T22.010 home, .012 runs, .015 psyche, .016 messages_voice, .017 shadow_goals, .021 settings, .030 chapter_board.

## Wave 4: P21 → P21A → TUI(D2) (25 + ~4 tasks)

- **P21 Learning** (blueprint 20 §7, 17 §6): every change goes through the inbox; rollback restores the previous version; LR-04 refuses
  changes that target rules, hard checks, truth/citation thresholds, or the adults-only constraint. Prompt trials are replay-based (F18),
  and a new prompt is promoted only if it improves with no regression.
- **P21A Recheck & Reason** (blueprint 26): it **never runs automatically**; the CLI requires confirmation and shows a cost estimate.
  Challengers run **blind** to the Keepers (their prompt inputs contain no StructureFindings), every exchange is MGE-graded, and challengers
  never edit text. The Promise Ledger finds every Ch1 promise and flags the provocation-spiral promise (OI-36: planted in ch03, taken
  apart in ch04, exited in ch12, **open to additions**, so read `profile/provocation_spiral_analysis.md §7` and don't hard-code the list).
  T21A.042 is **verify-only**: the note already exists in README.md and MUSE_START_HERE.md, so record the evidence and don't edit.
- TUI(D2): T22.034 audience_lab (a "Simulated readers" label assertion), .035 persona_studio (age 17 shows an error and doesn't save), .040
  learning_inbox, and the reason / intent / Recheck button + reminder parts of T22.043.

## Wave 5: T23.001–T23.003

`eval/run_eval.py` covers every goal in `system_goals.yaml` plus every gold metric, with the release-blocker summary at the top, and the
chaos suite from 14 §6.3 runs with `pytest -m chaos`. Build on `main` in `lane/d/w5` and merge through Muse-I.

## Risks specific to this lane

| Risk | Guard |
|---|---|
| Psyche output that diagnoses the author | Validators + a banned-label list + the "this passage shows…" phrasing test |
| An orchestrator that silently redoes work | Call-count assertions in the resume and chaos tests |
| K3 and K4 landing late and stalling B and C | Build them first in W2, get the shape ACKed before implementing |
| A TUI shell that other lanes can't extend | A key-registration API + one screen per file + a seeded DB covering every screen |
| Recheck & Reason being triggered by something other than the author | A test that no scheduler, act, or hook calls it |
