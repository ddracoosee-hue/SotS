# Communication protocol

The agents never share a working tree, so they talk only through the **coordination folder**. Files
are the source of truth. Any live channel, such as Claude Code's `SendMessage`, is only a nudge that
says "check your inbox". If something is decided anywhere else, it hasn't been decided until a file
here records it.

## 1. The coordination folder

Default location: `C:\Users\ddrac\sots-coord\` (AD-6). It sits outside every worktree and has its own
git repo. `scripts/setup_coord.ps1` creates it.

```
sots-coord/
  WAVE.md                    current wave, its lanes, exit criteria, merge order        (writer: I)
  status/<A|B|C|D|I>.md      one status card per agent                                  (writer: that agent)
  inbox/<A|B|C|D|I>/         messages to one agent; move each to inbox/<X>/done/ once handled
  broadcast/                 messages to everyone                                        (writer: I, or anyone for BLOCKER)
  cr/CR-####_<slug>.md       change requests                                             (writer: requester; status lines by I)
  contracts/CONTRACTS.md     every published interface: id, producer, version, main sha  (writer: I)
  merge_queue/<lane>_<phase>.md   READY-FOR-MERGE tickets                                (writer: lane; result by I)
  reviews/REV-<lane>-<phase>.md   peer verification reports                              (writer: the reviewing lane)
  evidence/<lane>/<phase>.md      per-task evidence log                                  (writer: lane)
  buildlog/<lane>.md         staged BUILD_LOG lines                                      (writer: lane; moved in by I)
  author_questions/<ts>_<agent>.md   questions for the author                           (writer: anyone; answered by I)
  DEFERRED.md                deferred-by-plan tasks and their state                      (writer: I)
  DECISIONS.md               append-only decision log (ADR style)                        (writer: I)
  profile_manifest.sha256    the sha256 of every file under profile/                      (writer: I)
```

**One writer per file.** Every file has exactly one writer, so no two agents ever write the same file.
Agents don't commit to the coordination repo; Muse-I commits a snapshot at every merge and every wave
boundary.

## 2. Messages

File name: `YYYYMMDD-HHMMSS_<from>_<TYPE>_<slug>.md` (local time; the timestamp orders them).

```markdown
---
from: B
to: C            # A|B|C|D|I|ALL
type: CR         # see the table
wave: W1
refs: [CR-0003, T08.030, blueprint/06 §5]
requires_ack: true
---
<one-paragraph summary: what, why, and what you need from the reader>

<details: signatures, file paths, test names, commit sha>
```

| Type | Use it when | Expected reply |
|---|---|---|
| `INFO` | FYI, no action needed | none |
| `QUESTION` / `ANSWER` | clarifying another lane's interface or behaviour | an ANSWER before the reader's next task |
| `CR` / `CR-ACK` / `CR-REJECT` | a change to something you don't own (§4) | ACK or REJECT with a reason, within one task cycle |
| `CONTRACT-LANDED` | I merged a contract or CR to `main` | the consumers merge at the SYNC |
| `SYNC` | I tells the lanes to merge `main` into their branch | do it at the next task boundary, then report in `status/` |
| `INSTALL-REQUEST` / `INSTALL-LANDED` | dependencies, tools, services (§6) | see §6 |
| `BLOCKER` / `RESOLVED` | you can't continue without someone else | the owner answers first, before any other work |
| `READY-FOR-MERGE` | a phase is closed with evidence (`BEST_PRACTICES.md §4`) | I assigns a reviewer |
| `REVIEW-REQUEST` / `REVIEW-RESULT` | peer verification (`BEST_PRACTICES.md §5`) | a report in `reviews/` |
| `MERGED` / `WAVE-START` | I finished a merge, or opened a wave | read `WAVE.md` |
| `AUTHOR-QUESTION` | only the author can answer | I relays it; never guess (15) |
| `STOP` | the author or I halts everyone (kill switch) | finish the current atomic edit, commit WIP to your lane branch, report, idle |

## 3. Cadence (every agent)

1. **Session start:** read `WAVE.md`, your inbox, and `broadcast/` since your last read. Then update `status/<you>.md`.
2. **Before each task:** check your inbox and broadcast. Handle any BLOCKER, CR, or SYNC first.
3. **Before committing anything outside your owned paths:** confirm the grant or CR in `OWNERSHIP_MAP.md` or `cr/`.
4. **After each task:** append its evidence entry, commit to your lane branch, and update your status card.
5. **At phase close:** post the READY-FOR-MERGE ticket and notify I.
6. **Before ending a session:** commit (a WIP commit is fine on your own branch) and write a `status/` handoff: what's done, what's in progress, what's next, open messages.

Status card format (`status/<X>.md`, overwritten each time):

```markdown
agent: Muse-B · worktree: C:\Users\ddrac\sots-wt\B · branch: lane/b/w1
wave: W1 · phase: P08 · task: T08.030 (in progress)
updated: 2026-10-01 14:22
last green: 7c1e2ab (ruff ✓ pyright ✓ pytest 512 ✓)
waiting on: CR-0004 ack from C
next: T08.031
```

## 4. Change requests (CRs)

**You need a CR for:** any edit outside your owned paths, your anchor blocks, or your granted files; any
change to an existing `models/` module; ALTERs to tables you don't own; changing an existing config key;
changing the signature or behaviour of a published contract; new shared test fixtures; and anything in §6.

**Lifecycle:**

```
OPEN ──► ACKED (owner + every affected lane) ──► APPROVED (I; + the author when a rule or dependency is involved)
     ──► IMPLEMENTED on branch contract/CR-#### (off main, by the requester unless the owner prefers to)
     ──► REVIEWED by the owner ──► LANDED on main by I ──► SYNC broadcast ──► CLOSED
```

The CR file holds: the problem, the exact proposed change (signatures, fields, defaults), who it affects,
the blueprint reference, the tests that prove it, and whether it's **additive** (new optional field, new
function, new table) or **breaking** (anything else).

- **Additive CR: fast track.** The owner's ACK plus I's approval is enough. It lands within the wave.
- **Breaking CR:** every consumer must ACK. I schedules it: either immediately with a SYNC, or at the next merge.
  If it touches the blueprint's intent, it goes to the author.
- **Rejected CR:** the reason is recorded. The requester works around it inside its own lane, or escalates to I.
- **Silence:** a CR with no ACK after two of the owner's task cycles gets escalated by I. It is never treated as approved.

## 5. Contracts and SYNC points

Contracts (K1, K2, K3, K4 in `WAVE_PLAN.md §5`, plus any additive CR another lane consumes) land on `main`
**before** the wave ends:

1. The producer builds the interface, its tests, and a docstring that names the blueprint section, on `contract/K#` off `main`.
2. The producer posts a CR marked `contract: K#`. The consumers ACK the shape before the code is final.
3. I merges the branch to `main`, runs the full gate, records it in `contracts/CONTRACTS.md` (version, sha), and broadcasts `CONTRACT-LANDED` + `SYNC`.
4. Every lane runs `git merge main` at its next task boundary, then reruns the full gate. It logs the result in its status card.
5. The producer's own lane branch also merges `main`, so the contract code isn't duplicated.

A contract is **frozen** once it lands. Changing it takes a new CR, and adding to it is a new version.

## 6. Installs, services, and machine-wide changes

These affect every agent, so **only Muse-I does them**, and only with the author's approval where the rules require it.

| Change | Rule |
|---|---|
| A Python dependency (add, remove, or upgrade) | R-CODE-01: **author approval**. INSTALL-REQUEST to I, stating what's needed, why the approved list can't do it, and the blueprint reference. I asks the author, then edits `pyproject.toml`, runs `uv lock` on `main`, commits, and broadcasts `INSTALL-LANDED` + `SYNC`. Every lane runs `git merge main` and then `uv sync --locked`. |
| `uv sync` in a lane | Only `uv sync --locked`. Never `uv add`, `uv lock`, `pip install`, or `uv pip install`. |
| Docker, SearXNG, LanguageTool, Java | I only, with author approval (OI-07, OI-21). Nobody needs them for offline tests. |
| Ollama model pulls or changes | I only, with author approval (OI-05). Tests never call Ollama (R-CODE-07). |
| `.env`, API keys | Author only (R-DATA-03). Lanes never read `.env` values into logs or messages. |
| Global git config, PATH, the Python install | Never. |
| `profile/` (the author's foundation) | Nobody. Changes go through Proposals (R-FOUND-02). |

## 7. Escalation

1. Lane ↔ lane: a QUESTION or CR in the owner's inbox.
2. Still no answer after the owner's next two task cycles, or the two lanes disagree: a BLOCKER to I. I decides from the blueprint and records the decision in `DECISIONS.md`.
3. The blueprint is silent, contradicts itself, or the decision belongs to the author: an AUTHOR-QUESTION. The lane
   builds the documented default where one exists (15 §A "default until answered"), marks it provisional, and moves on.
   It never guesses.
