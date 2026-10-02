# P09 — Media Accuracy

**Prerequisites:** P08. **Blueprint refs:** 07 (all).

- [ ] **T09.001** | `prompts/media/identify.v1.md` + `media/identify.py` | Extract the title/creator/year/kind guess; resolve via TMDB/OpenLibrary/MusicBrainz/Wikipedia by kind; token_sort_ratio ≥ 85; creator/year tie-breaks. | Tests: correct pick; ambiguous title (the year breaks the tie); unresolved.
- [ ] **T09.002** | `media/identify.py` | Identity errors → attribution MediaPoints (wrong year/creator). | Test.
- [ ] **T09.003** | `media/sources.py` | Gather the plot/summary sections, themes/reception sections, and up to 3 analysis/interview pages; all excerpt-verified; excerpts capped at 300 characters. | Tests: the cap enforced; no lyrics requested.
- [ ] **T09.004** | `prompts/media/media_check.v1.md` + `media/checker.py` | The MediaCheck agent with the interpretation ladder (07 §3) and the "personal reading is legitimate" framing rule. | FakeProvider test.
- [ ] **T09.005** | `media/postrules.py` | The downgrade rules of 07 §4. | One test per rule.
- [ ] **T09.006** | `media/media_stage.py` | Resumable over the MEDIA_REFERENCE units; runs concurrently with the verify stage. | Integration test.
- [ ] **T09.007** | `reports/sections/media.py` | The report section per 07 §5, including the framing suggestion for personal readings. | Snapshot test.
- [ ] **T09.008** | `classify/review_queue.py` | Add unresolved works to the review queue with the top-3 candidates; the author's confirmation re-runs the check. | Test.
- [ ] **T09.009** | `tests/unit/test_no_lyrics.py` | A guard test: no stored excerpt with source kind MUSIC exceeds 0 characters of lyric text (the lyric fetch endpoints are absent; media excerpts are length-capped). | Passes.
- [ ] **T09.090** | — | All green; BUILD_LOG line. | Done.
