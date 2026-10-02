# P11A — Voice Lab

**Prerequisites:** P11 (the narrative + voice baseline). **Blueprint refs:** 29 (all); it supersedes 09 §5 and 19 §1.2.
Only stdlib + rapidfuzz. Any NLP library (e.g. spaCy) requires the author's approval (R-CODE-01).

## Corpus intake
- [ ] **T11A.001** | `models/voice.py` | VoiceSample, FeatureValue, FeatureStat (μ, σ, n_eff, confidence, importance), VoiceModel (per register, versioned), TransformationProfile, SignatureMove, VoiceOverride (pin/relax/forbid). | Round-trip tests.
- [ ] **T11A.002** | `voice/corpus.py` | Folder sync over `profile/voice_corpus/{final,drafts,spoken,casual,pairs,not_me}`; supported formats via the P04 loaders; manifest maintenance (hash, words, register, weight, note); **Ch1 auto-registered** from `profile/manuscript/` as final ×2.0; duplicate detection. | Tests.
- [ ] **T11A.003** | `voice/corpus.py` | Pair detection (`name.raw.*` + `name.final.*`) → pair records. | Test.
- [ ] **T11A.004** | `cli.py` | `sots voice add|sync|profile|check "<text>"|pin|relax|forbid|snapshot|rollback`. | CLI tests.

## Features (≥ 120 total, 10 families; 29 §2)
- [ ] **T11A.010** | `voice/features/lexical.py` | F-LEX, incl. the standardized TTR, the Latinate-suffix heuristic, contraction rate, someone/somebody, and signature words via log-odds vs the reference. | Tests.
- [ ] **T11A.011** | `voice/features/syntax.py` | F-SYN (sentence stats, clause heuristic, initial conjunctions, questions, fragments, passive heuristic, parentheticals, triads). | Tests.
- [ ] **T11A.012** | `voice/features/rhythm.py` | F-RHY (the long→short alternation index, paragraph-final short sentences, anaphora). | Tests on Ch1 paragraphs (e.g. §1's "Seventy years after somebody drew a line with a pen.").
- [ ] **T11A.013** | `voice/features/punctuation.py` | F-PUN, incl. em-dash spacing and the serial comma. | Tests.
- [ ] **T11A.014** | `voice/features/numbers.py` | F-NUM (words vs numerals; study-mention pattern; caveat-follow rate). | Tests.
- [ ] **T11A.015** | `voice/features/annotated.py` + `prompts/voice/annotate_features.v1.md` | F-EPI, F-RHE, F-EMO via a temperature-0 annotation with a fixed schema, cached per sample hash; pattern-based counterparts where possible. | FakeProvider tests.
- [ ] **T11A.016** | `voice/features/discourse.py` + `person.py` | F-DIS, F-PER. | Tests.
- [ ] **T11A.017** | `voice/features/negative.py` | Negative features: AI clichés, corporate words, preambles, bracket tags, em-dash overuse; learned `not_me` contrasts. | Tests.
- [ ] **T11A.018** | `voice/reference/` | A bundled, license-clean general-English reference profile (public-domain essays + neutral generated prose), versioned; `ref_f`, `ref_sd_f` computed by a script checked into the repo. | The profile builds deterministically.

## Model + algorithm (29 §3)
- [ ] **T11A.020** | `voice/model.py` | Weighted μ/σ (trust × recency × √words), n_eff, confidence = n_eff/(n_eff+k), shrinkage toward the prior, per register. | Hand-calculation tests on a 3-sample fixture.
- [ ] **T11A.021** | `voice/model.py` | Importance = confidence × (0.45 consistency + 0.35 distinctiveness + 0.20 contrast). | Tests.
- [ ] **T11A.022** | `voice/model.py` | Recency with an 18-month half-life and a final-register floor of 0.6. | Tests.
- [ ] **T11A.023** | `voice/similarity.py` | VOICE(t) (29 §3.5): the z-scored fit per feature, importance-weighted numeric_sim, negative penalty, llm_sim via MGE seats P2/P9, and the corpus-confidence-dependent weighting. | Tests: held-out Ch1 paragraphs ≥ 0.8; an AI-cliché fixture ≤ 0.5.
- [ ] **T11A.024** | `voice/scaling.py` | Every scaled assessment in 29 §3.6 (thresholds, tolerances, reported features, E6 weight, R-SYN-07 bonus, protected-term discovery, confidence labels). Consumers read the scaled values from here, never hard-coded. | Monotonic tests as the corpus grows; Low-confidence failures → warnings, not blocks.
- [ ] **T11A.025** | `voice/overrides.py` | Pin/relax/forbid applied after learning; versioned; forbids feed the negative features and the Style Guide don'ts. | Tests.
- [ ] **T11A.026** | `voice/explain.py` + prompt | Plain-English explanations of the top features and the off-voice reasons, with sentence highlights. | Snapshot tests.

## Transformation model + moves (29 §4–5)
- [ ] **T11A.030** | `voice/transform.py` | Pair alignment (rapidfuzz sentence alignment) → feature deltas + a move library (kept verbatim / expanded / cut / aside→caveat) via `voice.align_pairs`; a confidence value. | Test on a fixture pair.
- [ ] **T11A.031** | `voice/moves.py` | Load `signature_moves.yaml`; extract candidate moves from new final samples (`voice.moves_extract`) → proposals to the author; the refrain flag; cross-chapter exact-phrase reuse detection → Repetition Manager. | Tests.
- [ ] **T11A.032** | `rewrite/style_guide.py` | Generate the StyleGuide from the VoiceModel (29 §7), replacing the seed-only build. | Test: the Ch1-derived guide contains the top features + the protected terms.
- [ ] **T11A.033** | wire-up | Style Analyst, Block Synthesis, Rewrite A/B, MGE E6, the Audience voice floor, and the Master Audit T-VOICE all read from `voice/similarity.py` + `voice/scaling.py`. | Integration test: changing the corpus changes the thresholds everywhere consistently.

## Author surfaces
- [ ] **T11A.040** | `tui/screens/voice_lab.py` (spec; built in P22) | Add material, the "what changed" diff, the profile view with confidence bars and register tabs, pin/relax/forbid, "does this sound like me?", one-key not-me marking, snapshots/rollback. | Registered in the P22 list.
- [ ] **T11A.041** | `reports/voice_profile.py` | `voice_profile.md`: the top 25 features in plain English, corpus confidence, the scaled thresholds in effect, and the signature moves. | Snapshot test.
- [ ] **T11A.090** | — | All green; BUILD_LOG line. | Done.
