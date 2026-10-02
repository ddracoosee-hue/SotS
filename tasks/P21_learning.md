# P21 — Learning Loop

**Prerequisites:** P20. **Blueprint refs:** 20 §7, 17 §6, 18 §4 (step 6), 01 LR rules via 20.

- [ ] **T21.001** | `learning/playbook.py` | Technique tagging of audience_edit hunks (the LLM tags from techniques.yaml, validated against the list). | Test.
- [ ] **T21.002** | `learning/playbook.py` | Outcome evaluation after re-test: success = the targeted metric +0.5 with no primary regression; Beta(α, β) update per technique × cohort × metric. | Tests with hand-computed posteriors.
- [ ] **T21.003** | `learning/playbook.py` | Suggestions for the brief writer: techniques with ≥ 10 trials and a posterior mean ≥ 0.6 (LR-02). | Test.
- [ ] **T21.004** | `learning/prompt_trials.py` | A/B a candidate prompt version: replay the recorded runs (F18) + the gold sets; promote only if the metrics improve and no release blocker regresses. | Test with fixture recordings.
- [ ] **T21.005** | `learning/inbox.py` | LearningChange lifecycle: proposed → applied/dismissed; apply = a versioned write to the config/prompt file; rollback restores the previous version. | Tests.
- [ ] **T21.006** | `learning/guards.py` | LR-04: refuse changes targeting the rules, hard checks, truth/citation thresholds, or the adults-only constraint. | Tests.
- [ ] **T21.007** | `learning/log.py` | Append to LEARNING_LOG.md per applied change (date, what, why, the evidence). | Test.
- [ ] **T21.008** | `learning/sources.py` | Collect the proposals: grader health alerts (P14), calibration unreliability (P16), reject-reason clusters (P19), and persona homogeneity trends. | Tests.
- [ ] **T21.009** | `cli.py` | `sots learning inbox|apply|rollback`. | Tests.
- [ ] **T21.090** | — | All green; BUILD_LOG line. | Done.
