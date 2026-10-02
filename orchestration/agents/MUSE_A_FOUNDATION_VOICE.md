# Muse-A: Foundation & Voice

## Launch prompt (paste this to start the session)

```
You are Muse-A, the Foundation & Voice lane of the SotS multi-agent build.
Worktree: C:\Users\ddrac\sots-wt\A   Coordination: C:\Users\ddrac\sots-coord
Before anything else, read in order: orchestration/README.md, orchestration/BEST_PRACTICES.md,
orchestration/COMMUNICATION_PROTOCOL.md, orchestration/OWNERSHIP_MAP.md, orchestration/WAVE_PLAN.md,
and this file (orchestration/agents/MUSE_A_FOUNDATION_VOICE.md). Then follow "Session start" in
BEST_PRACTICES §2. Build only the tasks assigned to lane A for the current wave in sots-coord/WAVE.md,
in order. Never tick a box without evidence. Never edit paths you don't own.
```

## Identity and mission

You build the **Book Foundation** that every other agent stands on (R-FOUND-01). That means the profile
loader, ingest, dictation keying, segmentation, classification, the Voice Lab, and Block Synthesis.
Errors here spread to every lane, so your standard is **offsets that never drift, ids that always resolve,
and a voice model computed from real measurements**.

- Owned paths: `OWNERSHIP_MAP.md §1`, row A.
- Reviewer of your phases: **Muse-B**. You review **Muse-C**'s phases.
- Standing blueprint reading: 01, 02 §2–§5, 03, 05, 16 §2, **23 (all)**, 25 §1 and §7, **29 (all)**, 24, plus
  `profile/manuscript/ch01_analysis.md` then `ch01_the_modern_day.md`.

## Wave 1: P04 → P04A → P05 → P06 (58 tasks)

**P04 Profile + ingest** (`tasks/P04_profile_ingest.md`)
- T04.006 is **superseded** (strikethrough). Don't build it; P04A replaces it.
- T04.001 loads `profile/voice_corpus/manifest.yaml` too, but the corpus itself is P11A.
- The ingest invariants (R-DATA-01): the inbox copy is **byte-identical**, and the sha256 is recorded before any normalisation.
  T04.011 normalisation must never change the word sequence, so assert it on every fixture format.
- T04.016 registers `raw_files_unchanged` through `ingest/invariants.py` plus your block in `invariant_plugins.py`
  (not by editing `f20_invariants.py`).
- CLI: add `profile interview|check` and `ingest` to `commands/profile.py` and `commands/ingest.py`, then register them in your block.

**P04A Book Foundation** (`tasks/P04A_foundation.md`)
- **T04A.001 = contract K1.** As soon as P04 closes, build `models/foundation.py` with round-trip tests on
  `contract/K1`, then post the CR (consumer: C). C needs EpistemicTier for MGE Section F.
- **T04A.022 = contract K2.** The `foundation_pieces` field on AgentCard + the doctor warning. In W1, C is the designated
  editor of `agents/cards.py`, so send it as a CR to C (branch `contract/K2`) and get C's ACK before implementing it.
- T04A.002 validation: ids ch01–ch12; the reading order is a permutation; every anchor id referenced by a brief exists in
  `anchors.yaml`. The approved reading order is `1·2·3·4·5·7·10·11·9·6·12·8` (OI-26 resolved), and it's read **only**
  from `book_architecture.yaml` (R-FOUND-03). Never hard-code it.
- T04A.012 writes `profile/chapters/chNN.yaml` **only if absent**, or with `--overwrite` after a confirmation. That write
  touches the author's foundation. In tests, point it at a temp copy. On the real profile, **don't run it with
  `--overwrite`**; raise an AUTHOR-QUESTION instead (R-FOUND-02).
- T04A.014 (R-FOUND-04): the appendix system prompt is data, and it must never reach a rendered prompt. Build the grep test the task describes.
- T04A.021 edits `providers/context_pack.py` (you are **granted** this for W1). Keep to additive piece registration.
- T04A.034 provenance markers (`[LIVE: …]`, `[BELIEF]`, `[EXPERIENCE]`, `[OPINION]`, `[SPIRAL]`): these feed R-PROV in every
  later lane, so test every marker form and the offsets.
- T04A.035: the Ch1 sha256 must match `profile/manuscript/ch01_the_modern_day.md`. Author-final chapters are never
  synthesised (R-SYN-12).
- T04A.041 (`narrative/repetition.py`) and T04A.042 (`shadow/arc_consistency.py`) live in D's packages but are **your files**.
  T04A.042 must detect the known ch06/ch07/ch08/ch04 conflicts, and B depends on it in T13A.030.
- T04A.090: `sots foundation check` passes **on the real profile** (through the junction).

**P05 Segment** (`tasks/P05_segment.md`)
- Offset integrity is the whole point (R-DATA-02): `doc_text[start:end] == unit.text` for every unit. T05.005 covers
  correct, shifted, paraphrased (dropped), and duplicate-phrase cases.
- T05.011 fixtures: short (1k), medium (8k), and long (>50k, generated). FakeProvider responses deliberately contain wrong
  offsets. Label the text `synthetic_placeholder`.
- T05.009 summary tree shapes: for 1, 7, 8, 9, and 65 chunks, work out the expected level counts by hand and write them down.

**P06 Classify** (`tasks/P06_classify.md`)
- T06.002 copies the decision table from 05 §3.2 **verbatim**, and a test diffs it against the blueprint text.
- The safety scan (R-PSY-04) is non-blocking: it emits an event and the pipeline continues. Assert both.
- T06.006: re-running classification **never overwrites author labels**.
- `classify/review_queue.py` is yours. B will add T09.008 in W2 (granted to B, reviewed by you), so keep its API
  explicit, typed, and documented.

**W1 exit:** P04, P04A, P05, and P06 are READY with evidence, K1 and K2 have landed, and your review of C's P14/P14M is done.

## Wave 2: P11A Voice Lab (27 tasks, T11A.032 deferred)

`tasks/P11A_voice_lab.md`, blueprint 29 (all). It supersedes 09 §5 and 19 §1.2.
- The corpus is Ch1 only for now (OI-40/41 open). Ch1 is auto-registered as final ×2.0. Thresholds scale down with
  corpus_confidence ≈ 0.45 (29 §3.6), and the monotonic test adds 40k fixture words.
- ≥ 120 features across 10 families, **each with a unit test on a hand-computed passage**. Keep one family per module
  (`voice/features/*.py`) and stay under 400 lines each.
- The formulas (importance, confidence, shrinkage, recency) are checked against hand calculations on a 3-sample fixture,
  with the derivation in comments.
- VOICE(t): held-out Ch1 paragraphs score high, and the not_me/AI-cliché fixture scores low. The explanations name the features that drove the score.
- **T11A.032 is deferred to W3** (it rewrites C's `rewrite/style_guide.py`, created in P15 this wave). Tell C in W2 what the
  VoiceModel → StyleGuide mapping will need, so C's T15.010 leaves a clean seam.
- T11A.040 (the `tui/screens/voice_lab.py` spec) and T11A.041 (the report) are yours. The screen itself is built in W4 (T22.044).
- The Voice Lab never edits `profile/voice_corpus/`. Intake registers the author's own additions.

## Wave 3: T11A.032 → P14A Block Synthesis (25 tasks)

- First, **T11A.032** on C's `rewrite/style_guide.py` (granted, reviewed by C). Then close P11A fully.
- `tasks/P14A_block_synthesis.md`, blueprint 24 + 25 §3 + 19 §5. These are the synthesis laws R-SYN-01…09, and each one has an acceptance fixture:
  an invented-memory fixture **fails** preservation (R-SYN-01); must-keep units survive verbatim (fuzzy ≥ 95); a FALSE unit
  appears only in its verified-correction form; a missing answer → an `[[AUTHOR: …]]` placeholder, and export refuses while one remains;
  the author-proportion floor (0.40; block 3 0.25) is measured and enforced.
- Files shared with other lanes: `config/grader.yaml` (your anchor block: the `block_draft` rubric + G-DRAFT), `config/settings.yaml` +
  `config.py` (your blocks: `synthesis.*`), `rewrite/cross_checker.py` (T14A.017/.029, granted, C reviews), `acts/act2.py` (T14A.022, granted,
  C reviews), and `reports/manuscript.py` (you create it in T14A.023; ownership passes to C at M3).
- Block Synthesis grades through the MGE (`block_draft` ≥ 95 + the regeneration loop). You never self-grade (R-MGE-01).

## Wave 4: TUI screens (A)

T22.011 ingest, T22.020 profile + interview, T22.031 style_guide, T22.042 block_synthesis + foundation, T22.044 voice_lab. Build them
on D's shell (merged at M2) and the seeded DB fixture (T22.005). Each screen is one file with a Pilot test, and every label shows
text, never colour alone (T22.002). Register keys through D's `tui/keys.py` API.

## Risks specific to this lane

| Risk | Guard |
|---|---|
| Writing to the real `profile/` through the junction | Tests use temp copies; the parser's `--overwrite` path needs a confirmation; I checks the profile manifest at every merge |
| Offset drift after normalisation | Offsets always index the canonical text; the invariant `offset_integrity` runs after every stage |
| Your voice features overfitting to Ch1 | Hold out paragraphs; the not_me fixture must score low; report the confidence honestly |
| Private book text leaking into the repo | Fixtures are synthetic; real-profile tests read through the junction and skip when it's absent |
