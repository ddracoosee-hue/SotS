# MUSE: START HERE

> **Status: SKELETON. The author will expand the Muse instructions later.**
> This file points to the blueprint and the task list. How Muse works (its workflow,
> reporting style, approvals, and so on) is intentionally left open for the author to define.

You are the coding agent building **SotS**, a terminal-based research, fact-checking,
rewriting, audience-testing, and legal-review system for the author's self-help / reflective
book for **adult readers**: *The Subject of the Self* by Caleb Crouch. The book's 12 chapter
briefs, core messages, voice, anchors, and proposed architecture live in `profile/` and are the
**foundation** every agent works from (`blueprint/23_BOOK_FOUNDATION.md`).

## Reading order

Read these in this order. The file numbers are stable IDs; they don't show the reading order.

| Step | File | Contents |
|---|---|---|
| 1 | `blueprint/01_RULES.md` | Hard laws. They override everything else. |
| 2 | `blueprint/02_ARCHITECTURE.md` | System overview, **the six Acts**, folder tree, dependencies. |
| 3 | `blueprint/03_DATA_MODELS.md` | Core data structures (the team docs add their own). |
| 4 | `blueprint/04_PROVIDERS_AND_CONTEXT.md` | Model providers (Muse API adapter left open), routing, large context. |
| 4b | `blueprint/23_BOOK_FOUNDATION.md` | **The book (The Subject of the Self) as every agent's foundation**: files, context cards, Act 0, dictation keying. Then skim `profile/`. |
| 4b+ | `profile/manuscript/ch01_the_modern_day.md` + `ch01_analysis.md` | **The author-final Chapter 1: the reference chapter for voice, form, and honesty.** Read the analysis first. |
| 4b++ | `blueprint/29_VOICE_LAB.md` | **The author's voice model**: the intake folder, 120+ features, a confidence-weighted algorithm, assessments that scale with the data, the Transformation Model, the Signature Moves Library. |
| 4c | `blueprint/25_EPISTEMIC_STANDARD_AND_SCRIPTURE.md` | The author's [Documented Fact]/[Primary Theory]/[Interpretive Extension] tiers, evidence grades, scripture checks. |
| 5 | `blueprint/16_AGENT_RUNTIME_AND_FAILSAFES.md` | **The shared agent runtime, tools, internet access, failsafes F01–F20.** |
| 6 | `blueprint/05_INGEST_SEGMENT_CLASSIFY.md` | Act I, stages 1–3. |
| 7 | `blueprint/06_FACT_CHECK_PROTOCOL.md` | Act I, stages 4–5 + the Fact-Check Team and its scouts (§9). |
| 8 | `blueprint/07_MEDIA_ACCURACY.md` | Act I, stage 6. |
| 9 | `blueprint/08_PSYCHE_ENGINES.md` | Act I, stage 7. |
| 10 | `blueprint/09_NARRATIVE_AND_VOICE.md` | Act I, stage 8. |
| 11 | `blueprint/10_SHADOW_SELF.md` | Act I, stage 9 (+ the final grade in Act VI). |
| 11b | `blueprint/27_MASTER_GRADING_ENGINE.md` | **The single judge every agent relies on**: Factual + Emotional grading, the Professional Perspective Panel, stability, one master answer (no rerolls). |
| 12 | `blueprint/17_QUALITY_GATE_GRADER.md` | The ≥ 95 gate in front of every author-facing output. |
| 12b | `blueprint/24_BLOCK_SYNTHESIS.md` | Act II-D: drafting each block from fact-checked dictation. |
| 13 | `blueprint/19_POLISH_AND_REWRITE_TEAMS.md` | Act II (Pass A) and Act VI (Pass B): rewriters, Style Analyst, Reference Cross-Checker. |
| 14 | `blueprint/21_TARGET_AUDIENCE_RESEARCH.md` | Adult audience research + the Reader Mind Model. |
| 15 | `blueprint/20_AUDIENCE_LAB.md` | Act III: text-mechanics analysts, adult persona panel, learning loop. |
| 16 | `blueprint/22_LEGAL_CHAMBER.md` | Act IV: the eight counsel and the cohesive defense. |
| 17 | `blueprint/11_EXPANSION_TEAM.md` | Act V: concept mapping, deep research, dialogue, pitching. |
| 18 | `blueprint/18_PROPOSAL_DESK.md` | Act V: how agents bring projects to the author. |
| 18b | `blueprint/26_STRUCTURE_REASONING_AND_COUNTER_COUNCIL.md` | Recheck & Reason: the Intent Keepers + the Counter-Council (on request only). |
| 18c | `blueprint/28_MASTER_AUDIT.md` | The end section: a verified test battery → the Master Version (a milestone tool). |
| 19 | `blueprint/12_TERMINAL_UI.md` | CLI + TUI. |
| 20 | `blueprint/13_BUILD_PHASES.md` | Build order P00–P25 with acceptance checks. |
| 21 | `blueprint/14_TESTING_AND_EVAL.md` | Tests, gold sets, chaos tests, system goals. |
| 22 | `blueprint/15_OPEN_ITEMS.md` | Unresolved decisions. Never guess these. |
| 23 | `tasks/00_TASK_INDEX.md` | **The master task list: every task, numbered, in build order.** |

## Note for the author (keep visible)

> **Recheck & Reason is available whenever you want it.** Run `sots reason` (or press the
> TUI button) to have the Intent Keepers re-examine the book's structure from the
> psychological perspective of what you're trying to communicate, and the Counter-Council
> challenge the ideas. It never runs on its own. SotS reminds you when enough has changed to
> make a recheck worthwhile.
>
> **Voice Lab:** you can add any of your writing to `profile/voice_corpus/` at any time (the
> README there explains how). Every addition sharpens the voice model, and every voice check
> scales with it.

## Blueprint status (finalized 2026-09-29)

The blueprint is **complete enough to build from**: 29 spec files, the `profile/` foundation, and
**620 tasks across 31 phases** (`tasks/00_TASK_INDEX.md`).

> **Resuming? Start from the beginning, then find where things left off.** Read the files above in
> order, then check `BUILD_LOG.md`, `git log`, and the checked boxes in `tasks/`. Don't trust the boxes:
> re-verify each finished phase from P00 up. The current plan and the author's latest decisions are in
> `orchestration/NEXT_STEPS.md`. (Updated 2026-10-02 at the author's request.)

**Open items never block a phase.** Each one in `15_OPEN_ITEMS.md` has a "default until
answered". Build with that default, keep it switchable in config, and label it provisional.
Only tasks marked **[author verifies]** stop for the author.

| Phases | What they depend on from the author | Build with |
|---|---|---|
| P00–P01 | nothing | — |
| P02 Providers | OI-03 (Muse API details), OI-05 (local model), OI-06 (privacy), OI-09 (budget) | the Muse adapter behind an interface with a stub + tests; route to local; defaults as listed |
| P03, P07 Research tools | OI-07 (search provider), OI-08 (API keys) | SearXNG; key-gated fetchers disabled cleanly |
| P04–P04A Foundation | OI-02 (core messages, draft v0), OI-28 (brief edits), OI-30 (author profile) | the drafts in `profile/`, flagged as drafts |
| P11A Voice Lab | OI-40 (raw→final pairs), OI-41 (more writing) | Ch1 only; the thresholds scale down automatically (29 §3.6) |
| P13A Act 0 | — (OI-36 approved) | verify the `*.PS*` anchors like any other; the serial stays open to additions (`profile/provocation_spiral_analysis.md` §7) |
| P14–P15 | OI-13, OI-15, OI-19, OI-21, OI-22 | defaults; Pass A needs the Style Guide approved (OI-15) before it *runs*, not before it is *built* |
| P16–P17 | OI-16, OI-17, OI-18, OI-23, OI-24, OI-31 | the template personas (unreviewed); US-primary law; anonymize by default |
| P25 | — | **LOCKED.** Never build it. |

**Settled decisions (do not reopen):** chapter order `1·2·3·4·5·7·10·11·9·6·12·8` · NASB 2020,
with a per-quote translation choice · named influencers kept and verified · prose-style
evidence signals · Ch1's form is foundational but can be modified · the infinite bookshelf is
credited to Peterson (live, Tulsa 2024) · the Ch2 character types are context-dependent (the
four promised types must appear) · no regenerate button anywhere; revise-with-note only ·
Recheck & Reason runs only on request · the provocation spiral is planted in ch03, taken apart in ch04 and exited in ch12 (approved; open to additions).

## Non-negotiables (already fixed)

1. The rules in `blueprint/01_RULES.md` apply.
2. Build the phases in the order given in `blueprint/13_BUILD_PHASES.md`, working the tasks in
   `tasks/` in numeric order. Each phase's acceptance checks must pass before the next phase
   starts.
3. If something is unclear, add a question to `blueprint/15_OPEN_ITEMS.md`. Do not guess.

## Muse operating instructions

<!-- AUTHOR: define Muse's workflow, reporting, approval gates, persona, etc. here. -->
_To be written by the author._
