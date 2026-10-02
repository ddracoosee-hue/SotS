# P14A — Block Synthesis (Act II-D)

**Prerequisites:** P14 (Grader) + P04A + P13A. **Blueprint refs:** 24 (all), 19 §5, 25 §3.

## Models + config
- [ ] **T14A.001** | `models/synthesis.py` | Beat, BlockPlan, BlockDraft (24 §3). | Round-trip tests.
- [ ] **T14A.002** | `config/grader.yaml` | Add the `block_draft` rubric (24 §6) + the gate G-DRAFT. | Weights-sum test.
- [ ] **T14A.003** | `config/settings.yaml` | `synthesis.target_words_by_block`, `synthesis.author_proportion_floor` (0.40; block 3: 0.25), `synthesis.max_attempts`. | Config test.
- [ ] **T14A.004** | `config/agents/synthesis/*.yaml` | Cards: assembler (deterministic), architect, synthesizer, preservation_auditor, stitcher; foundation_pieces F1–F6 as appropriate. | doctor validates.

## Agents
- [ ] **T14A.010** | `synthesis/assembler.py` | Gather the block material (24 §2). Units are ordered by prompt then position; verified corrections are attached; the motif-serial instruction for this chapter/block; the previous block's draft tail. | Test.
- [ ] **T14A.011** | `prompts/synthesis/plan.v1.md` + `synthesis/architect.py` | BlockPlan generation; must-keep detection (manuscript quotes, signature lines, lines the author marked, strong lines from any earlier audience run). | FakeProvider test.
- [ ] **T14A.012** | `synthesis/plan_check.py` | Every unit accounted for (used | dropped with a reason); drop reasons from the enum; FALSE units can't be `verbatim`. | Tests.
- [ ] **T14A.013** | `prompts/synthesis/draft.v1.md` + `synthesis/synthesizer.py` | Draft the prose with sentence provenance + tier tags; inline tags only for the science/statistics kinds (25 §3); `[[AUTHOR: …]]` placeholders for unanswered prompts. | FakeProvider test.
- [ ] **T14A.014** | `synthesis/preservation.py` | R-SYN-01 (first-person experiential claim extraction → unit match), R-SYN-02 (must-keep fuzzy ≥ 95), R-SYN-07 (the author proportion from the provenance). | Tests: an invented-memory fixture fails; a missing must-keep fails; the proportion is computed.
- [ ] **T14A.015** | `synthesis/structure_check.py` | R-SYN-05: block-specific structure (old/new belief present; Before/Action/Result; protocols with *verified* grades; journaling prompts). | A test per block type.
- [ ] **T14A.016** | `synthesis/arc_check.py` | R-SYN-06: motif appearances match the serial plan; callbacks use reading-order chapter numbers. | Tests.
- [ ] **T14A.017** | `rewrite/cross_checker.py` | Extend it: verify that every inline tier tag equals the computed tier; no DEBUNKED support; HEDGE items use approved hedges; composite cases are disclosed. | Tests.
- [ ] **T14A.018** | `prompts/synthesis/stitch.v1.md` + `synthesis/stitch.py` | Seam sentences only (≤ 2 per seam, origin SYSTEM). | Test: any non-seam change is rejected.

## Act wiring + author control
- [ ] **T14A.020** | `acts/act2d.py` | Per block 1→6: assemble → plan → check → draft → (preservation ∥ style ∥ cross-check) → G-DRAFT ≥ 95 (regenerate ≤ max) → accept; then stitch → the chapter draft becomes Revision A0 for Pass A. | Integration test with FakeProvider over a fixture chapter.
- [ ] **T14A.021** | `acts/act2d.py` | Author controls: lock a block (skip synthesis), keep-verbatim units, regenerate with a note. | Tests.
- [ ] **T14A.022** | `acts/act2.py` | Pass A now starts from the Act II-D output (or the author's locked text). | Test.
- [ ] **T14A.023** | `reports/manuscript.py` | Export refuses while any `[[AUTHOR: …]]` placeholder remains; lists them. | Test.
- [ ] **T14A.024** | `cli.py` | `sots act II-D <chapter> [--block N] [--lock N] [--note "…"]`. | Test.
- [ ] **T14A.025** | `tui/screens/block_synthesis.py` (built in P22; registered now) | The screen spec: plan view, draft with origin colors, placeholders list, regenerate-with-note. | Added to the P22 screen list.
- [ ] **T14A.026** | `eval/synthesis_gold/` | 3 fixture blocks with the author's dictation + a human-approved draft; the metrics: preservation pass, author proportion, voice similarity. | The metrics compute.
- [ ] **T14A.027** | `synthesis/provenance.py` | R-PROV-02/03 in synthesis: belief units keep first-person belief framing; live-source units get prose attribution + an endnote; unverifiable sources use "author-attested" framing. | Tests: a `[BELIEF]` rewritten as fact fails; a missing attribution fails. |
- [ ] **T14A.028** | `synthesis/form.py` | R-SYN-10…12: section layout from the Chapter Form Template (foundational, modifiable per chapter: OI-35; deviations are allowed when the BlockPlan records a story-driven reason); honest-limits section + instrument with a notebook step + bridge present; `author_final` chapters are skipped. | Tests. |
- [ ] **T14A.029** | `rewrite/cross_checker.py` | Prose-style tier verification (25 §3): each science/statistics claim carries a prose signal matching its computed tier. | Tests with Ch1 sentences as positive fixtures. |
- [ ] **T14A.090** | — | All green; BUILD_LOG line. | Done.
