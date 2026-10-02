# P11 — Narrative + Voice

**Prerequisites:** P10. **Blueprint refs:** 09 (all).

- [ ] **T11.001** | `narrative/messages.py` | Load CoreMessages from messages.yaml; a graceful "messages missing" mode. | Tests.
- [ ] **T11.002** | `prompts/narrative/map_messages.v1.md` + `narrative/ledger.py` | Batches of 25 → MessageMapping; the role weights; the emphasis ranking + emphasis gaps. | Tests with a hand-computed ranking.
- [ ] **T11.003** | `narrative/drift.py` | unmapped_ratio, drift_segments (≥ 5 units, ≥ 80% unmapped), missing_messages; chapter suggestion for unsorted text. | Tests on fixtures.
- [ ] **T11.004** | `narrative/flow.py` | The deterministic jump detection + one batched LLM confirmation call. | Tests.
- [ ] **T11.005** | `narrative/fingerprint.py` | Every VoiceFingerprint metric (09 §5.1). | Tests on a tiny known text with hand-computed values.
- [ ] **T11.006** | `narrative/voice.py` | The LLM style description (cached by the samples hash) + similarity = 0.5 numeric + 0.5 LLM; deviations; off-voice units. | Tests.
- [ ] **T11.007** | `narrative/voice.py` | `local_similarity(text_a, text_b, context)` for hunk-level voice checks (reused by the Style Analyst in P15). | Test.
- [ ] **T11.008** | `narrative/narrative_stage.py` | Stage wiring; resumable. | Integration test.
- [ ] **T11.009** | `reports/sections/narrative.py` | Coverage bars (text), emphasis gaps, drift map, voice panel. | Snapshot test.
- [ ] **T11.090** | — | All green; BUILD_LOG line. | Done.
