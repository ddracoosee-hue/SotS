# eval/grader_gold — Hand-graded gate artifacts (blueprint 14 §6.1)

Expected contents: 20 artifacts (proposals, rewrite hunks, legal memos, and
other gate-judged items), each hand-graded per criterion against the rubrics
in `config/grader.yaml` (see 17 §3.1–§3.5 and 22 §5).

Used for: judge agreement — LLM judges must agree within ±1 point of the
hand grades on ≥ 80% of criteria (17 §6; system goal
`grader.judge_agreement_within_1 >= 0.80`).
