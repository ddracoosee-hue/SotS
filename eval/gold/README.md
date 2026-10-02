# eval/gold — Hand-labeled quality passages (blueprint 14 §3)

Hand-labeled passages that measure real Act I quality. **The author helps build this.**

Expected contents:

```text
eval/gold/
  passages/gp01.md …   # 10–20 passages written in the author's style
  labels/gp01.yaml     # expected labels per passage
```

Label format per passage (`labels/gpXX.yaml`):

```yaml
passage: gp01
units:
  - text: "exact substring"
    content_type: factual_claim
    claim_kind: statistic
    checkability: checkable
    expected_verdict: partially_true   # the human fact-checker's judgment
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

Composition target: ≥ 60 labeled units total, including ≥ 10 statistics,
≥ 5 legal cases, ≥ 5 social media cases, ≥ 5 academic findings,
≥ 8 media references, ≥ 5 **deliberately false** claims, and ≥ 5 misleading ones.

Used by: `sots eval` (confusion matrices, adjacent-verdict agreement,
most-missed claim kinds) — see 14 §4–§5.
