# Best practices for working together

These practices apply to all five agents. When two sources conflict, the one earlier in this list wins:
**`blueprint/01_RULES.md` → the other blueprint files → the task line → this pack → your own judgment.**
If you find a conflict, record it (`COMMUNICATION_PROTOCOL.md §7`). Don't resolve it silently.

## 1. Prime directives

1. **Never guess.** If the blueprint doesn't say, use the documented default from 15 §A, mark it
   provisional, and raise an AUTHOR-QUESTION. A wrong guess costs more than a question.
2. **A checkbox is a claim that the check passed.** Tick a box only after running its "Done when"
   check and logging the output (§3). An unticked box that's honestly labelled is better than a
   ticked box that's false.
3. **Stay in your lane.** Edit only the paths `OWNERSHIP_MAP.md` gives you. Everything else goes
   through a CR.
4. **Never weaken a check to get green.** Don't delete, skip, `xfail`, loosen, or rewrite a failing
   assertion to match wrong output, and don't raise a tolerance or add a `# type: ignore` / `noqa`
   without a written reason in the evidence log. Fix the code instead.
5. **The author's material is sacred.** Never edit `profile/`, `MUSE_START_HERE.md`, `blueprint/`
   (except I's append to 15), `.env`, or `supplements/`. Author recommendations go to the author as
   yes/no questions. Nothing is applied on the author's behalf.
6. **There's no regenerate path anywhere** (R-MGE-04). If output needs to change, revise it with a
   note that gets recorded.

## 2. Session start (every time, including after a context reset)

1. Read `orchestration/README.md` §2 and your own `agents/MUSE_<X>.md`.
2. Read `sots-coord/WAVE.md`, your inbox, `broadcast/`, and your `status/<X>.md` handoff.
3. Run `git status` and `git log --oneline -5` in your worktree, and confirm you're on your lane branch.
4. Run the gate (`scripts/verify_lane.ps1`) before you change anything. If it's red and you didn't
   cause it, stop and post a BLOCKER to I. Don't build on a red base.
5. Read the blueprint sections your next task cites **in full** before you write code. Also read the
   neighbouring task lines, because they often constrain each other.

## 3. The definition of done for a task

- [ ] The test was written first and seen to **fail for the right reason** (red), then pass (green).
- [ ] The "Done when" check from the task line was run literally, and its output was captured.
- [ ] Every rule the code enforces is cited in a comment (`# R-TRUTH-02`, `# VR-STAT-03`, `# 06 §7`).
- [ ] Hand-computed test values show their derivation in a comment (the inputs, the formula, the result).
- [ ] No inline prompts (R-LLM-02); model calls happen only in `providers/` (R-LLM-01); there's no `print()`
      outside `cli.py`/`commands/`/`tui/` (R-CODE-08); every cross-module object is a Pydantic model (R-CODE-04).
- [ ] Every new persisted record has an F07 idempotency key and a round-trip test.
- [ ] Every new agent has an Agent Card with its mandatory failsafes; internet agents have F03, F13, F14, F15.
- [ ] Every file is ≤ 400 lines (R-CODE-03).
- [ ] `ruff check` on the touched paths, `pyright`, and the relevant tests are all green.
- [ ] An evidence entry is appended, and the commit is made on your lane branch.

**Evidence entry** (`sots-coord/evidence/<lane>/<phase>.md`, append only):

```markdown
### T08.036 · 2026-10-01 15:40 · commit 4be91c0
done-when: "Tests, including a TRUE capped by 3 rules."
ran: uv run pytest tests/unit/test_verify_rules_caps.py -q  → 9 passed
red first: yes (the assertion min(TRUE, caps) failed with NotImplementedError)
rules cited: R-TRUTH-03, VR-GEN-01..07
notes: fiction → CONTEXT is applied before the other caps (06 §5.1)
```

## 4. Phase close (the `.090` task)

1. The full gate is green on a clean tree: `ruff check .`, `pyright`, `pytest` (run **twice**; a flaky test counts as a failure),
   `sots doctor` (from P03), and `sots eval` with no release-blocker regression (from P13 on, once K4 exists).
2. Walk every item in the cross-cutting checklist in `tasks/00_TASK_INDEX.md` for the code this phase added,
   and record the result per item in the evidence log. (Only I ticks those boxes, at the merge.)
3. Check that every task in the phase has an evidence entry. Deferred tasks are listed in `DEFERRED.md`.
4. Stage the build-log line in `sots-coord/buildlog/<lane>.md` using the existing `BUILD_LOG.md` format.
5. Post a READY-FOR-MERGE ticket in `merge_queue/<lane>_<phase>.md` with: the branch, the head sha, the gate output
   summary, the new migrations, the anchor blocks touched, the CRs consumed or produced, the deferred tasks, and known limitations.
6. Keep working on your next phase while the ticket waits, but don't rewrite the history the ticket points to.

## 5. Peer verification (the two-key close)

No phase merges on its author's word alone. Every READY ticket gets an independent review by the lane that
**consumes** that code:

| Producer | Reviewer | Why |
|---|---|---|
| A | B | B's fact-check and brief audit consume units, foundation, and anchors |
| B | D | D's Act I orchestration wires verify and media |
| C | A | A's Block Synthesis grades through the MGE and uses the Style Guide and cross-checker |
| D | C | C's MGE Section E, Pass B, and P24 consume psyche, audience, and orchestration |

The reviewer follows this procedure:
1. `git worktree add --detach C:\Users\ddrac\sots-wt\review-<lane>-<phase> <sha>`, then add the profile junction and run `uv sync --locked` there.
2. Run the full gate. Rerun the "Done when" check for **every** task that enforces a hard rule (R-TRUTH, R-GATE, R-AUD,
   R-LEGAL, R-MGE, R-PSY, R-SYN, R-PROV, R-EXP) and for at least 30% of the rest, picked at random and listed.
3. Read the diff (`git diff w<k>-start..<sha> -- <lane paths>`) looking for: weakened or deleted tests, `skip`/`xfail`,
   new `noqa`/`type: ignore`, inline prompts, HTTP or SQL outside the allowed modules, invented URLs, DOIs, or quotes in
   code or fixtures, edits outside owned paths, files over 400 lines, and missing rule citations.
4. Try one **adversarial input** per hard rule (a planted invented excerpt, an under-18 persona, a paraphrased "quote",
   an echo of the prompt) and confirm the code rejects it.
5. Write `reviews/REV-<lane>-<phase>.md` with the verdict **PASS**, **PASS-WITH-NOTES**, or **FAIL**, and a line per finding
   (the file, the line, what's wrong, and the evidence). Send REVIEW-RESULT to the producer and to I.
6. Remove the review worktree afterwards (`git worktree remove`).

A FAIL goes back to the producer. The fix happens on the same lane branch, and the reviewer re-checks only the findings.
Reviews come before your own next task. Keep them rigorous but proportionate, and don't redesign the other lane's code.

## 6. Accuracy practices for this codebase

- **Synthetic fixtures must look synthetic.** Use `example.org`, `*.test` domains, and text marked
  `synthetic_placeholder`. Never put a real-looking URL, DOI, case citation, ISBN, statistic, or quote in a fixture
  unless it was fetched and verified (R-TRUTH-01). The whole system exists to catch fabrications, so its own test data
  mustn't contain any.
- **Determinism:** tests use FakeProvider scripts, respx mocks, an injectable clock, and seeded randomness. There's no
  network access, no sleeping, and no dependence on the order in which tests run.
- **Use the real foundation where the task says to** (for example T04A.090 "passes on the real profile" or the Ch1 fixtures).
  The foundation comes through the read-only junction. Don't copy profile text into the repo (it's private,
  R-DATA-04). Tests that need it skip cleanly with a clear message when `profile/` is absent.
- **Resumability** (R-CODE-06): every stage has a kill-and-resume test that proves nothing was redone (count the calls).
- **Contracts over internals:** import another lane's code only through the functions and models listed in
  `contracts/CONTRACTS.md` or its package's public `__init__`. Don't reach into another lane's private helpers.
- **Measure, don't ask the LLM:** measured criteria and numbers in reports come from code (16 §4, R-GATE-02).
- **Adults only** (R-AUD-01) and **simulated readers** labels (R-AUD-02) are asserted in tests, not assumed.

## 7. Git hygiene

- Branches: `lane/<a|b|c|d>/w<k>` (a new one each wave, cut from `main` at `w<k>-start`), `contract/K#` or
  `contract/CR-####`, `fix/<lane>/<slug>`. Only I commits to `main`.
- Keep commits small and scoped to one task. The message is `T08.036: apply_caps min-by-strength (R-TRUTH-03, 06 §5)`,
  followed by the attribution trailer your harness requires.
- Stage explicit paths (`git add src/sots/verify/rules.py tests/unit/test_verify_rules_caps.py`). Check `git status`
  before every commit. Never commit `data/`, `profile/`, `.env`, `.venv/`, or caches.
- Never `push --force`, `reset --hard` on a shared branch, rebase `main`, or touch another worktree's folder.
- Merge `main` into your branch only when a SYNC is broadcast or a wave starts. Never merge another lane's branch directly.
- Line endings: W0 adds `.gitattributes` (`* text=auto eol=lf`), so agents on different tools don't produce
  CRLF churn. Don't renormalise files you don't own.

## 8. Preventing conflicts

- Keep one responsibility per module (R-CODE-03), and create new files rather than growing shared ones.
- Don't format, rename, re-sort imports, or "tidy" code outside your paths, even when the tool offers to.
- Append inside your anchor block only, at the end of your block, one registration per line.
- Take migration numbers from your range. Don't reuse a number, even after deleting the file.
- Announce early. If you realise mid-task that you'll need a shared change, send the CR **immediately**, then keep
  working on something else while it's reviewed.
- When unsure whether something is a contract change, treat it as one.

## 9. Windows and tooling specifics

- Use `uv run …` for every project command. Bare `py` resolves to Python 3.14, and this project is 3.12 only.
- PowerShell 5.1 has no `&&`. Use `cmd; if ($?) { next }`. Pass `-Encoding utf8` when writing files.
- Each worktree has its own `.venv` (created with `uv sync --locked`) and its own `data/` (created with `uv run sots init`).
  Never point two worktrees at the same `data/sots.db`, because SQLite WAL files and locks will collide.
- `profile` in a worktree is a **junction** to the main checkout's `profile/`. `Remove-Item` on the junction deletes the
  link, but a recursive delete through it deletes the author's files. Never run a recursive delete on `profile`.
- ENVIRONMENT_READY.md reports that the Codex sandbox runner sometimes times out while connecting its pipe. If commands fail
  before they start, report it in `status/` and ask I; don't retry in a loop.

## 10. Long sessions and handoffs

- Before a long operation, and whenever your context is getting large, update `status/<X>.md` with a precise handoff: the last
  finished task, the uncommitted state, the next step, and any open CRs or messages.
- A fresh session must be able to continue from `status/` + `evidence/` + `git log` alone. If it couldn't, the handoff isn't done.
- Don't re-derive settled facts. The decisions in `DECISIONS.md` and the ✅ RESOLVED rows in 15 stay closed.

## 11. Anti-patterns (if you notice one, stop)

- A box ticked because "the code looks right", without running the check.
- A test changed after it failed so that it now matches the code.
- "Temporarily" editing another lane's file to unblock yourself.
- Building against another lane's unmerged branch.
- Running `uv add` / `pip install` to fix an import error.
- A fixture that contains a plausible real citation.
- A module that quietly grows past 400 lines.
- Leaving a CR unanswered because you're "almost done".
- Reporting "all green" without the command output to back it up.
