# 14 — TESTING AND EVALUATION

## 1. Test layers

| Layer | Folder | Uses | Runs by default |
|---|---|---|---|
| Unit | `tests/unit/` | pure functions, rules, metrics, validators | yes |
| Integration | `tests/integration/` | FakeProvider + respx-mocked HTTP + a temporary SQLite DB | yes |
| TUI | `tests/tui/` | Textual Pilot + a seeded DB | yes |
| Live | `tests/live/` | real Muse / Ollama / APIs, `@pytest.mark.live` | no (`pytest -m live`) |

Coverage target: ≥ 85% lines on `verify/`, `research/`, `expand/report_validator.py`,
`segment/`; ≥ 70% overall.

## 2. FakeProvider fixtures
- `tests/fixtures/llm/<task>/<name>.json`: canned outputs.
- FakeProvider matches on `(task, input_hash)`, and falls back to `(task, "default")`.
- It records every request it receives, so tests can assert what context was sent.
- It includes "bad" fixtures: invalid JSON, schema violations, wrong offsets, fake ids,
  injected instructions.

## 3. Gold set (`eval/gold/`)

Hand-labeled passages that measure real quality. **The author helps build this.**

```
eval/gold/
  passages/gp01.md …            # 10–20 passages written in the author's style
  labels/gp01.yaml              # expected labels
```

Label format:
```yaml
passage: gp01
units:
  - text: "exact substring"
    content_type: factual_claim
    claim_kind: statistic
    checkability: checkable
    expected_verdict: partially_true     # the human fact-checker's judgment
    expected_basis: academic
    notes: "real figure is 40%, from 2019"
  - text: "…"
    content_type: personal_experience
    checkability: not_checkable
media:
  - text: "…"
    work: {title: "…", year: 1999}
    expected_points: [{statement: "…", accuracy: inaccurate}]
    expected_status: plausible_personal_reading
```

Composition target: ≥ 60 labeled units total, including ≥ 10 statistics, ≥ 5 legal cases,
≥ 5 social media cases, ≥ 5 academic findings, ≥ 8 media references, ≥ 5 **deliberately
false** claims, and ≥ 5 misleading ones.

## 4. Metrics computed by `sots eval`
Everything in `config/system_goals.yaml` (`10 §3` and `11 §5`), plus:
- a confusion matrix of content_type and of verdict
- adjacent-verdict agreement (one step apart on the strength order counts as adjacent)
- the most-missed claim kinds
Output: `data/runs/eval_<date>.md` + `.json`. The history is kept, so regressions are visible.

## 5. Regression rule
If any release-blocker metric (`==0` / `==1.0` targets) is worse than on the previous eval,
the current build phase is **not done**, even if all its unit tests pass.

## 6. Additions for the new teams

### 6.1 New gold sets
| Folder | Contents | Used for |
|---|---|---|
| `eval/grader_gold/` | 20 artifacts (proposals, hunks, memos) hand-graded per criterion | judge agreement ±1 on ≥ 80% (17 §6) |
| `eval/rewrite_gold/` | 10 paragraphs with known errors + the author's intended corrections + intentional style quirks | Mechanic precision/recall; protected-term preservation = 100% |
| `eval/legal_gold/` | 12 synthetic passages with known legal issues (fictional people/cases) + the expected issue types and a risk level | intake recall ≥ 0.9; risk agreement ≥ 0.75 |
| `eval/audience_gold/` | Real beta-reader responses (once available, adults only) | calibration correlation (20 §6) |
| `eval/proposal_gold/` | 10 proposals the author accepted/rejected | usability grader agreement |

### 6.2 New system goals (append to `config/system_goals.yaml`)
```yaml
rewrite:
  protected_terms_preserved:     {target: "==1.0"}
  meaning_preservation_pass:     {target: "==1.0"}
  mechanic_precision:            {target: ">=0.95", how: "accepted suggestions that were real errors"}
  mechanic_recall:               {target: ">=0.90"}
  cross_check_drift_escapes:     {target: "==0",   how: "drifted items found in gold that the cross-checker missed"}
grader:
  judge_agreement_within_1:      {target: ">=0.80"}
  below_bar_leak:                {target: "==0",   how: "items shown to the author with score < 95"}
legal:
  legal_fabricated_authority_rate: {target: "==0"}
  intake_recall:                 {target: ">=0.90"}
  banner_presence:               {target: "==1.0"}
audience:
  adults_only_violations:        {target: "==0"}
  caricature_marker_escapes:     {target: "==0"}
  synthetic_real_correlation:    {target: ">=0.5", how: "per metric, once real data exists"}
runtime:
  invariant_violations:          {target: "==0"}
  dead_letter_rate:              {target: "<=0.02"}
  resume_success:                {target: "==1.0", how: "chaos test: kill at random steps, resume"}
```

### 6.3 Chaos tests (`tests/chaos/`, run with `pytest -m chaos`)
- Kill the process at random agent steps (20 random seeds) → resume → the final DB state
  equals an uninterrupted run.
- Inject a 30% failure rate into fetchers → circuit breakers open, the run completes in
  degraded mode, and the reports say so.
- Inject malformed LLM outputs at a 20% rate → retries + dead letters, with no crash.
- Corrupt a checkpoint file → detected, the run restarts that agent from scratch, and it is logged.
