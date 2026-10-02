# 12 — TERMINAL UI (CLI + TUI)

There are two front ends over the same core. **Neither contains business logic.** They call
functions in `pipeline/`, `expand/`, `storage/repo.py`, and `reports/`.

## 1. CLI (`src/sots/cli.py`, Typer)

| Command | Does |
|---|---|
| `sots init` | Creates `data/`, the DB, and the `profile/` + `config/` templates if missing. Idempotent. |
| `sots profile interview` | The guided interview: writes `profile/author.md` and `profile/book.md`. |
| `sots profile check` | Validates the profile files and lists what is missing. |
| `sots ingest <path> [--chapter ch03] [--title "…"]` | Stage 1. Prints the doc_id. |
| `sots run <doc_id>… [--stages 2-9] [--dry-run] [--budget N]` | Runs the pipeline. `--dry-run` prints the token/cost estimate only. |
| `sots resume <run_id>` | Continues a stopped or failed run (R-CODE-06). |
| `sots status [<run_id>]` | Stage table, unit counts, tokens used. |
| `sots report <run_id> [--open]` | Writes `data/runs/<run_id>/report.md` + `report.json`. |
| `sots claims <run_id> [--verdict false] [--kind statistic]` | Prints a filtered claims table. |
| `sots expand map \| propose \| approve <thr> \| research <thr> \| dialogue <doc> \| integrate <rep>` | Stage 11. |
| `sots audit` | System audit (`10 §3`). |
| `sots eval` | Runs the gold-set evaluation (`14`). |
| `sots settings test-providers` | Health-checks each configured provider and fetcher. |
| `sots cost [--since DATE]` | Token and cost summary from `llm_calls`. |
| `sots tui` | Launches the TUI. |
| `sots write …` | Prints "Writer is disabled (R-SCOPE-02)" and exits with code 2. |

Exit codes: 0 ok, 1 error, 2 disabled feature, 3 budget exceeded, 4 needs author input.

## 2. TUI (`src/sots/tui/`, Textual)

### 2.1 Layout
```
┌ SotS ─ <book title> ─ run: <id> ─ tokens 412k/2M ─ provider: muse ✔ local ✔ ─────────┐
│ [sidebar]            │ [main screen]                                                 │
│  Home                │                                                               │
│  Ingest              │                                                               │
│  Runs                │                                                               │
│  Claims              │                                                               │
│  Media               │                                                               │
│  Psyche              │                                                               │
│  Messages & Voice    │                                                               │
│  Shadow & Goals      │                                                               │
│  Expansion           │                                                               │
│  Review queue (n)    │                                                               │
│  Profile             │                                                               │
│  Settings            │                                                               │
├──────────────────────┴───────────────────────────────────────────────────────────────┤
│ status line: current stage · progress · warnings (budget, safety notice, fallbacks)  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Screens (build exactly these)

| Screen | Contents | Key actions |
|---|---|---|
| **Home** | Latest runs, goals met per chapter, open hard goals, pending approvals | `r` new run, `enter` open |
| **Ingest** | File picker + a paste box; chapter selector | `ctrl+s` ingest |
| **Runs** | Run list; live stage progress bars | `s` start, `p` pause, `R` resume |
| **Claims** | DataTable: unit text · kind · author-facing label · confidence · sources count. Filters by label/kind/chapter | `enter` claim detail |
| **Claim detail** | The author's words (highlighted in context), verdict, what's accurate / off, evidence list with excerpts, skeptic's objections, rule checks, suggested correction | `o` open source URL, `a` mark addressed, `n` add note |
| **Media** | Per-work cards: identity ✔/✘, retelling points table, reading status, alignment | `c` confirm work identity |
| **Psyche** | The board (filter by engine/severity), the synthesis panel, the emotion heat strip | `enter` jump to text |
| **Messages & Voice** | Coverage bars, emphasis gaps, drift map, voice score + deviations | `enter` jump to segment |
| **Shadow & Goals** | Shadow items as question cards; rubric table current → target ✔/✘; sparklines per criterion; system audit panel | `a` addressed, `w` waive hard goal (asks for a reason) |
| **Expansion** | Tabs: *Concept map* (a text-based graph list: hubs/bridges/orphans, with edges), *Threads* (approval queue with estimates), *Reports* (a readable report with origin colors), *Margin* (the document with margin notes beside it), *Chat* | `y` approve, `x` reject, `enter` open, `i` integrate |
| **Review queue** | Low-confidence classifications, unresolved media works, failed items | number keys relabel |
| **Profile** | Profile files, chapter briefs, messages. Validation status | `e` open in `$EDITOR` |
| **Settings** | Read-only view of config + provider health checks | `t` test providers |

### 2.3 Visual rules
- Origin colors (R-EXP-01): AUTHOR = default text, SOURCE = cyan, SYSTEM = magenta italic.
- Verdict label colors: Directly true / Academically supported / Reported true = green;
  Partially true = yellow; False = red; Could not verify = grey; Social media story =
  orange; From fiction = blue; Personal/narrative = dim.
- Never use color alone: every colored label also shows its text.
- Long-running work runs in Textual workers. The UI never freezes. Progress comes from the
  orchestrator's event queue.
- Safety notice (R-PSY-04): a dismissible banner, never a modal that blocks work.

## 3. Additions for Acts II–VI

### 3.1 CLI additions
| Command | Does |
|---|---|
| `sots doctor` | F17 health check (runs automatically before every act) |
| `sots stop` | F16 kill switch |
| `sots act <II\|III\|IV\|V\|VI> <chapter_id>` / `sots advance <chapter_id>` | Run a specific act, or the next eligible act |
| `sots chapter status [<chapter_id>]` | Act, gates, blocked reasons per chapter |
| `sots style-guide build \| show \| approve` | Style Guide lifecycle (19 §1.2) |
| `sots revisions list <chapter_id>` / `sots revisions diff <rev_a> <rev_b>` | Revision history |
| `sots hunks review <revision_id>` | Terminal hunk-by-hunk accept/reject (Pass B) |
| `sots audience run <revision_id>` / `import <csv>` / `questionnaire` | Audience Lab (20) |
| `sots legal status` / `sots legal issue <id>` / `sots legal waive <id> --attorney-confirmed --reason "…"` | Legal Chamber (22) |
| `sots proposals list \| show \| decide \| archive` | Proposal Desk (18) |
| `sots grader health` | Grader calibration signals (17 §6) |
| `sots learning inbox \| apply <id> \| rollback <id>` | Learning loop (20 §7) |
| `sots export <chapter_id\|all>` | Master output (19 §6) |
| `sots replay <run_id>` | F18 deterministic replay |

### 3.2 New TUI screens (added to the sidebar under "Workshop")
| Screen | Contents | Key actions |
|---|---|---|
| **Chapter Board** | One row per chapter: Act I–VI progress, gate lights (A, Legal, B), blocked reasons | `enter` open chapter, `n` advance |
| **Style Guide** | The editable Style Guide, protected terms, examples; approval state | `e` edit, `a` approve |
| **Revision Review** | Side-by-side before/after per hunk, with change type, reason, agent, grade, and style/cross-check badges; origin colors | `y` accept, `x` reject, `u` undo, `A` accept all of one change type (e.g. spelling) |
| **Style & Cross-Check** | StyleReport + CrossCheckReport for the selected revision; failing items highlighted | `enter` jump to hunk |
| **Audience Lab** | Scorecard (cohort bars), Journey curve J1–J7, hotspots, strong lines, persona reactions (filter by persona/cohort); a **"Simulated readers" label on every panel** (R-AUD-02) | `p` open a persona card, `r` re-run |
| **Persona Studio** | Create and edit persona cards; the diversity coverage matrix; the adults-only validator | `n` new, `e` edit |
| **Legal Chamber** | Banner (R-LEGAL-00); issue list with status/risk; per issue: the memo, endorsements, dissents, round transcripts; blocked items with options | `enter` open, `w` waive (requires the attorney-confirmed flag + reason) |
| **Proposal Desk** | Up to 7 open proposal cards; each shows its pitch, found material, placements, modes, questions, risks, and grade breakdown | `a` accept (pick P#/M# + answer questions), `m` modify, `d` defer, `x` reject (reason), `c` chat with the proposer |
| **Didn't Make the Cut** | The below-bar archive with every attempt's grade | `p` promote (logged override) |
| **Grader Health** | Pass rates, judge disagreement, author-reject clusters | — |
| **Learning Inbox** | Proposed prompt/threshold/persona/rubric changes with evidence | `y` apply, `x` dismiss, `r` rollback |
| **Export** | Export status, files produced, audit bundle summary | `x` export |

## 4. Additions: MGE, Recheck & Reason, Master Audit, Foundation
| Screen / element | Contents |
|---|---|
| **Recheck & Reason button** (Home + Chapter Board) | Always visible, with a quiet note: "Recheck & Reason is available: re-examine structure and ideas whenever you want." It is highlighted (never a popup) after a material change since the last run. |
| **Recheck & Reason screen** | Scope/focus picker, cost estimate + confirm, progress by team, the Reasoning Report, challenges with outcomes (defended / revise / open), the Promise Ledger, history diff |
| **Intent screen** | The Author Intent Model entries: confirm/edit, provisional flags |
| **Grade Inspector** | Any artifact's MGE grade: F and E section scores, per-criterion evidence, panel seat notes, blocking notes, the MGE version |
| **Revise with note** | Replaces any "regenerate" affordance everywhere: a text box for the note → a recorded input → re-run → one master output (R-MGE-04) |
| **Master Audit screen** | The battery version, the tests and their fixtures, results by family, the certification level, the audit history |
| **Voice Lab screen** (29 §6) | Add material (register, weight, note) + the "what changed in your voice profile" diff; the Voice Profile (top 25 features in plain English, confidence bars, register tabs); pin / relax / forbid; "Does this sound like me?" check with sentence highlights; one-key "not me" on any system output; snapshots + rollback. The Home screen shows a quiet line: "Voice Lab: add writing any time; every addition sharpens the voice checks." |
| **Manuscript view** | Author-final chapters (read-only), with claim/tier/provenance overlays and the Promise Ledger markers |

CLI: `sots reason …`, `sots mge stability`, `sots revise <artifact_id> --note "…"`, `sots master-audit …`, `sots voice add|sync|profile|check|pin|relax|forbid|snapshot|rollback` (29).
