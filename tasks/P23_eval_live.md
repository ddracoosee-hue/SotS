# P23 — Evaluation + Live Shakedown

**Prerequisites:** P22. **Blueprint refs:** 14 (all), 10 §3, 21 status note.

- [ ] **T23.001** | `eval/run_eval.py` | Compute every goal in system_goals.yaml (all sections) + the grader/rewrite/legal/proposal/audience gold metrics; write `eval_<date>.md/.json`; compare with the previous eval; flag regressions. | Runs end-to-end on the placeholder gold sets.
- [ ] **T23.002** | `eval/run_eval.py` | The release-blocker summary at the top of the report (every `==0` / `==1.0` goal). | Test.
- [ ] **T23.003** | `tests/chaos/*` | The chaos suite from 14 §6.3 (kill, fetcher failures, malformed outputs, corrupt checkpoint). | `pytest -m chaos` passes.
- [ ] **T23.004** | `eval/gold/README.md` | Instructions for the author to build the real gold sets (templates + label format + the composition targets from 14 §3 and §6.1). | The author can follow them.
- [ ] **T23.005** | — | **[author verifies]** Fill in the Muse API config (OI-03), local model (OI-05), search (OI-07), and keys (OI-08); `sots doctor` is green. | Doctor is green.
- [ ] **T23.006** | — | **[author verifies]** `sots run --dry-run` on one real chapter; the author approves the budget. | Approved.
- [ ] **T23.007** | — | **[author verifies]** Live Act I on one real chapter; review the claims, media, and shadow reports. | Reviewed.
- [ ] **T23.008** | — | **[author verifies]** Live Acts II–IV on the same chapter (Style Guide approved first). | Gates recorded.
- [ ] **T23.009** | — | **[author verifies]** Live Act V: at least one proposal decided; Act VI; export. | Export produced.
- [ ] **T23.010** | — | Ingest `blueprint/21_TARGET_AUDIENCE_RESEARCH.md` as a document and run Act I on it: **SotS fact-checks its own audience research.** Record any corrections in 15_OPEN_ITEMS §B. | Report produced; corrections logged.
- [ ] **T23.011** | — | `sots audit` after the live run; every release blocker passes. | The audit passes.
- [ ] **T23.012** | `BUILD_LOG.md` | The final P23 line with a summary of the live metrics. | Done.
