# P12 — Shadow Self + Rubrics + System Audit

**Prerequisites:** P11. **Blueprint refs:** 10 (all).

- [ ] **T12.001** | `prompts/shadow/shadow_reflect.v1.md` + `shadow/reflect.py` | ShadowItems in the 7 categories; ≤ 15, ranked; previous reports included as input; "addressed" items suppressed when their units are unchanged. | Tests.
- [ ] **T12.002** | `shadow/validators.py` | Valid unit ids; a non-empty question; a category in the allowed list; R-PSY-01/02 checks. | Tests.
- [ ] **T12.003** | `shadow/metrics.py` | The measured criteria of rubrics.yaml computed from the DB (factual_integrity, evidence_quality, media_fidelity, message_clarity, on_track, voice_consistency). | A test per metric.
- [ ] **T12.004** | `shadow/bands.py` | A band expression parser (">=0.95", "<=1.5", "==1.0", "<0.50") → a score. | Tests on every band form.
- [ ] **T12.005** | `prompts/shadow/rubric_grade.v1.md` + `shadow/rubric.py` | Judged criteria via the LLM with anchors + unit citations; the overall weighted mean; met flags. | Test: an LLM score for a measured criterion is ignored.
- [ ] **T12.006** | `shadow/goals.py` | Hard goals, trend vs the previous run of the same chapter, chapter-ready status, waivers (stored with a reason in the `waivers` table). | Tests.
- [ ] **T12.007** | `shadow/system_audit.py` | Computes every goal in system_goals.yaml that has data; reports "no data" otherwise; writes `audit_<date>.md`. | Test.
- [ ] **T12.008** | `cli.py` | `sots audit`. | Test.
- [ ] **T12.009** | `reports/sections/shadow.py` | Question cards, the rubric table, goals met/total, trend arrows. | Snapshot test.
- [ ] **T12.090** | — | All green; BUILD_LOG line. | Done.
