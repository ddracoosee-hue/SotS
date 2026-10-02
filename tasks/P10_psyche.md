# P10 — Psyche Engines

**Prerequisites:** P09. **Blueprint refs:** 08 (all), 01 §D.

- [ ] **T10.001** | `psyche/board.py` | Board post/read/facts_for/media_for over the engine_findings table (append-only). | Tests.
- [ ] **T10.002** | `psyche/registry.py` | The engine list + layers + dependencies; a topological execution plan. | Test: the layer order is enforced.
- [ ] **T10.003** | `prompts/psyche/emotion.v1.md` + `engines/emotion.py` | The Emotion engine with the exact finding-type vocabulary. | Test: an unknown finding type is rejected.
- [ ] **T10.004** | `prompts/psyche/cognitive.v1.md` + `engines/cognitive.py` | The Cognitive engine; passage-level phrasing; `sound_reasoning` positives. | Test.
- [ ] **T10.005** | `prompts/psyche/theme.v1.md` + `engines/theme.py` | Theme engine. | Test.
- [ ] **T10.006** | `prompts/psyche/archetype.v1.md` + `engines/archetype.py` | Archetype & Arc (layer 2). | Test: the layer-1 findings appear in its prompt input.
- [ ] **T10.007** | `prompts/psyche/blindspot.v1.md` + `engines/blindspot.py` | Blind Spot (layer 2): `_possible` types only + a required question. | Tests for both validators.
- [ ] **T10.008** | `prompts/psyche/reader.v1.md` + `engines/reader.py` | Reader Impact (layer 3, per document), using the adult target reader definition from 21 §1. | Test.
- [ ] **T10.009** | `psyche/validators.py` | Common validators: ≥ 1 valid unit id; the banned clinical labels absent (safety.yaml); "the author has" phrasing rejected (R-PSY-01); at least one strength per engine when present. | Tests.
- [ ] **T10.010** | `psyche/triggers.py` | TR-01…TR-07 as pure functions. | One test each.
- [ ] **T10.011** | `prompts/psyche/synthesize.v1.md` + `psyche/synthesizer.py` | Synthesis with id validation (cited ids must exist). | Test.
- [ ] **T10.012** | `psyche/psyche_stage.py` | Runs the layers per chunk/document, then the triggers, then the synthesizer. Resumable. | Integration test.
- [ ] **T10.013** | `reports/sections/psyche.py` | The board summary, synthesis, and emotion heat strip (a text sparkline). | Snapshot test.
- [ ] **T10.090** | — | All green; BUILD_LOG line. | Done.
