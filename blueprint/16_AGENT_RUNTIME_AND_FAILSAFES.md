# 16 — AGENT RUNTIME, TOOLS, AND FAILSAFES

Every agent in every team (fact-check, expansion, rewrite, audience, legal, grader,
proposal) is built on **one shared runtime**. Muse builds this runtime once (build phase P03)
and every later agent reuses it. **Never write a one-off agent loop.**

---

## 1. Agent Cards (`config/agents/<team>/<agent>.yaml`)

Every agent is declared in a YAML card. The card is the single source of truth for what the
agent may do.

```yaml
name: reference_cross_checker_a        # unique, snake_case
team: rewrite_pass_a                   # see the team list in §6
role: "Verifies every fact, number, name, quote and citation in revised text"
prompts:
  system: rewrite/cross_checker.system.v1.md
  step:   rewrite/cross_checker.step.v1.md
output_model: sots.models.rewrite.CrossCheckReport
routing_task: rewrite.cross_check      # key in routing.yaml
tools: [db_read_units, db_read_evidence, fetch_url, parse_html, web_search]
internet: true
limits:
  max_steps: 12                        # tool-use iterations
  max_tokens: 60000                    # per invocation, input + output
  timeout_s: 600
  max_retries: 2                       # on invalid output (R-LLM-03)
grading:
  rubric: null                         # or a rubric id in config/grader.yaml
failsafes: [F01, F02, F03, F04, F05, F06, F08, F09, F10, F12, F13]
on_failure: dead_letter                # dead_letter | escalate_to_author | degrade
```

Loader rules (`agents/cards.py`):
- Validate every card against a Pydantic `AgentCard` model at startup. Any invalid card →
  `sots doctor` fails, and the app will not start.
- The prompt files must exist. The routing task must exist. Every tool must be registered.
- The `failsafes` list must include the team's mandatory failsafes (§5.2).

## 2. Base agent (`src/sots/agents/base.py`)

```python
class AgentContext(BaseModel):
    run_id: str
    act: str                            # "I".."VI" (see 02 §2A)
    card: AgentCard
    inputs: BaseModel                   # typed per agent
    context_pack: ContextPack
    budget: BudgetSlice                 # tokens/cost allowed for this invocation
    checkpoint_key: str                 # stable key for resume

class BaseAgent(Generic[InT, OutT]):
    card: AgentCard
    async def run(self, ctx: AgentContext) -> AgentResult[OutT]
```

The lifecycle is fixed and implemented once in `BaseAgent.run`. Subclasses implement only
`build_step_variables()` and, optionally, `postconditions()`.

```
1. PRECHECK    inputs valid? tools healthy? budget available? kill switch off?
2. RESUME      if a checkpoint exists for checkpoint_key → load its state
3. LOOP        for step in 1..max_steps:
                   call_structured(step prompt) → AgentAction
                   if action.type == "final": break
                   execute tool (sandboxed, with failsafes) → observation
                   append observation (trimmed) to the scratchpad
                   checkpoint(state)
4. VALIDATE    parse final output → output_model (retry ≤ max_retries)
5. POSTCHECK   subclass postconditions (e.g. every cited id exists)
6. GRADE       if card.grading.rubric → Quality Gate (17) → regenerate loop
7. PERSIST     store the result + AgentRun record, emit event "agent.done"
```

### 2.1 The tool-use protocol (provider-independent)
The Muse API's tool-calling support is unknown (OI-03), so tools use a **JSON action
protocol** that works with any model:

```python
class AgentAction(BaseModel):
    type: Literal["tool", "final"]
    tool: str | None                 # must be in card.tools
    args: dict | None
    thought: str                     # ≤ 60 words, logged, never shown as fact
    final: dict | None               # validated later against output_model
```
- The runtime executes the tool and returns an `Observation(tool, ok, content, truncated)`.
- Observations are wrapped as `<observation tool="…">…</observation>` and treated as data
  (R-EXP-04 applies to every agent, not just expansion).
- If a provider supports native tool calling, `providers/` may map this protocol onto it,
  but the rest of the code only ever sees `AgentAction`.

### 2.2 AgentRun record
```python
class AgentRun(BaseModel):
    id: str; run_id: str; agent: str; team: str; act: str
    started_at: datetime; finished_at: datetime | None
    steps: int; tokens_in: int; tokens_out: int; cost: float
    status: Literal["ok", "failed", "dead_letter", "escalated", "degraded", "cancelled"]
    failure_code: str | None          # e.g. "F04_LOOP_DETECTED"
    grade_attempts: int
    final_grade: float | None
    checkpoint_key: str
```

## 3. Tool registry (`src/sots/agents/tools/`)

| Tool | Internet | Does | Guardrails |
|---|---|---|---|
| `web_search` | yes | Queries the configured search providers (04 §7) | ≤ 10 results; queries logged |
| `fetch_url` | yes | Fetches a page/PDF → `FetchedDoc` (06 §3.2) | robots.txt, 15 s timeout, 5 MB cap, per-domain rate limit |
| `parse_html` | no | Extracts text, headings, and tables from fetched HTML | output ≤ 20k chars per call |
| `parse_pdf` | no | pypdf text by page range | ≤ 30 pages per call |
| `parse_table` | no | HTML/CSV/JSON table → rows (`list[dict]`) with column types | ≤ 2000 rows; numeric parsing is locale-aware |
| `compute` | no | Safe arithmetic/statistics over parsed rows (mean, pct change, ratio) | **no eval()**; a whitelisted expression parser only |
| `courtlistener` / `openalex` / `crossref` / `google_factcheck` / `tmdb` / `openlibrary` / `musicbrainz` / `wikipedia` | yes | Structured lookups (06 §3.2) | keys from .env; disabled cleanly if a key is missing |
| `languagetool` | local | Spelling/grammar suggestions (19 §2) | local server only; the text never leaves the machine |
| `db_read_units` / `db_read_evidence` / `db_read_findings` / `db_read_profile` | no | Scoped read access to the DB | **read-only**; scoped to run_id/document |
| `excerpt_verify` | no | `citation_check.verify_excerpt` | deterministic |
| `persona_card` | no | Loads a persona (20) | read-only |

Agents **never write to the DB directly.** They return outputs, and the runtime persists them.

## 4. Numbers the LLM never produces

Any number that ends up in a report (a statistic, percentage, score, or count) is either
(a) copied from a fetched source and excerpt-verified, or (b) computed by the `compute` tool
or deterministic code. Scores produced by LLM judges are allowed only where a document
explicitly defines a judged criterion, and they are stored with `judged=True`.

## 5. Failsafes

### 5.1 Catalogue (`src/sots/agents/failsafes/`)

| ID | Name | Behaviour |
|---|---|---|
| **F01** | Timeout | Every tool call and agent invocation has a timeout from the card. On expiry: cancel, record, go to F02. |
| **F02** | Retry with backoff | Transient errors (network, 429, 5xx) retry up to 3 times, with exponential backoff + jitter (tenacity). Non-transient errors do not retry. |
| **F03** | Circuit breaker | Per provider and per tool: 5 consecutive failures → open for 60 s → half-open test → closed. While open, calls fail fast and the agent uses a fallback or degrades. |
| **F04** | Loop detection | Same tool + same args 3 times, or 2 consecutive steps with no new information (observation hash unchanged) → force a `final` with status `degraded`, code `F04_LOOP_DETECTED`. |
| **F05** | Schema guard | Output validation + repair retry (R-LLM-03). Also rejects outputs that echo the prompt or contain `<observation>` tags. |
| **F06** | Checkpointing | State is saved after every step under `checkpoint_key`. A crash + resume continues from the last step. |
| **F07** | Idempotent writes | Every persisted record has a deterministic idempotency key `(run_id, agent, input_hash)`. A duplicate write is a no-op. |
| **F08** | Dead-letter queue | Items that fail permanently go to `dead_letters` with the full reason + inputs. They are shown in the TUI Review queue and can be re-run individually. |
| **F09** | Watchdog | Agents emit a heartbeat per step. No heartbeat for `2 × timeout_s / max_steps` (minimum 60 s) → cancel and requeue once; the second time → dead letter. |
| **F10** | Budget guard | Hierarchical budgets: run → act → team → agent invocation. Exceeding a slice stops that agent cleanly and marks it `degraded`, and the rest of the team continues. |
| **F11** | Degraded mode | When a provider or tool is unavailable: use the fallback provider, skip the tool, and **cap the confidence/grade** (e.g. VR-GEN-07). Always labeled `degraded` in reports. |
| **F12** | Output sanity | Rejects empty outputs, outputs over the length limits, the wrong language, repeated paragraphs (≥ 3 identical sentences), and placeholder text ("lorem", "TODO", "[insert"). |
| **F13** | Injection guard | Observations are wrapped as data. A detector flags imperative patterns aimed at the model in fetched text ("ignore previous", "you are now", "system prompt") and strips them, logging `F13_INJECTION_STRIPPED`. |
| **F14** | Politeness | Per-domain rate limit (default 1 request/second), robots.txt respected, identifying User-Agent from settings. |
| **F15** | Size guard | Caps on fetched bytes, parsed characters, rows, and observation length (trimmed with a note, never silently). |
| **F16** | Kill switch | `sots stop` or the file `data/STOP` → all agents finish their current step, checkpoint, and exit. |
| **F17** | Doctor | `sots doctor` checks the config, cards, prompts, providers, tools, keys, disk space, DB integrity, and the LanguageTool server. Runs automatically before every run. |
| **F18** | Record/replay | `--record` saves every provider/tool response. `--replay <run_id>` re-runs deterministically from the recordings (debugging + tests). |
| **F19** | Canary | Before a full run over > 20k words, run Act I on a 1-page canary fixture. If it fails, abort before spending the budget. (Can be disabled in settings.) |
| **F20** | Invariants | After every act, check: offset integrity, citation validity, raw files unchanged (sha256), every finding cites existing ids, and no orphaned records. A violation → the run is paused with status `INVARIANT_BROKEN`. |

### 5.2 Mandatory failsafes per team

| Team | Mandatory |
|---|---|
| All teams | F01 F02 F05 F06 F07 F08 F10 F12 F16 F20 |
| Any agent with `internet: true` | + F03 F13 F14 F15 |
| Any agent with `max_steps > 1` | + F04 F09 |
| Rewrite teams | + F11 (degrade to "no change" rather than a bad change) |
| Legal Chamber | + F09, and escalation instead of dead letter for BLOCKED items |

## 6. Team registry (`config/teams.yaml`)

```yaml
teams:
  fact_check:        {doc: "06 §9",  act: I}
  media:             {doc: "07",     act: I}
  psyche:            {doc: "08",     act: I}
  narrative:         {doc: "09",     act: I}
  shadow:            {doc: "10",     act: [I, VI]}
  rewrite_pass_a:    {doc: "19 §3",  act: II}
  audience_lab:      {doc: "20",     act: [III, VI]}
  legal_chamber:     {doc: "22",     act: [IV, VI]}
  discovery:         {doc: "06 §9.3 + 11", act: V}
  quality_gate:      {doc: "17",     act: "all user-facing gates"}
  proposal_desk:     {doc: "18",     act: V}
  rewrite_pass_b:    {doc: "19 §4",  act: VI}
  learning:          {doc: "20 §7",  act: "after VI"}
```

## 7. Events

The runtime emits events onto an in-process async queue (`agents/events.py`):
`agent.start`, `agent.step`, `agent.tool`, `agent.grade`, `agent.done`, `agent.failed`,
`gate.pass`, `gate.fail`, `act.start`, `act.done`, `author.input_needed`.
The TUI subscribes to them, and the logger writes them to `data/logs/events.jsonl`.
