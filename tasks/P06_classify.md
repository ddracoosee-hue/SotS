# P06 — Classify + Safety Scan

**Prerequisites:** P05. **Blueprint refs:** 05 Stage 3, 01 R-PSY-04, R-TRUTH-05.

- [x] **T06.001** | `prompts/classify/safety_scan.v1.md` + `classify/safety_scan.py` | Batches of 20 units → flags; sets `safety_flag`; emits the `author.input_needed` event with type `safety_notice` (non-blocking). | Tests: a flagged fixture; the pipeline continues.
- [x] **T06.002** | `prompts/classify/classify_unit.v1.md` | The decision table from 05 §3.2 **verbatim**, plus 7 worked examples (one per ContentType). | The prompt validates.
- [x] **T06.003** | `classify/classifier.py` | Per-unit classification with a context pack (pieces 1, 2, 3, 7). | FakeProvider test.
- [x] **T06.004** | `classify/consistency.py` | `validate_consistency(out)` implementing the 4 rules in 05 §3.2 → the error list used in the retry prompt. | One test per rule (pass + fail).
- [x] **T06.005** | `classify/embedded.py` | embedded_claims → child units (parent_unit_id, same span, re-classified as FACTUAL_CLAIM). | Test.
- [x] **T06.006** | `classify/review_queue.py` | Query + relabel API: `relabel(unit_id, fields)` sets labeled_by="author"; re-running classification never overwrites author labels. | Tests.
- [x] **T06.007** | `classify/classify_stage.py` | A resumable stage over all units, with batching + concurrency. | Resume test.
- [x] **T06.008** | `cli.py` | `sots review list|relabel <unit_id> --type ...` (a CLI stand-in for the TUI review queue). | Test.
- [x] **T06.009** | `classify/stats.py` | Per-document counts by content_type/claim_kind/checkability, for reports. | Test.
- [x] **T06.090** | — | All green; BUILD_LOG line. | Done.
