# P03 — Agent Runtime, Tools, Failsafes

**Prerequisites:** P02. **Blueprint refs:** 16 (all), 01 R-AGENT-01, R-EXP-04.
This is the most important infrastructure phase. Every later team depends on it.

## Agent cards
- [x] **T03.001** | `agents/cards.py` | `load_cards(config/agents) -> dict[name, AgentCard]`; validates that the prompts exist, the routing task exists, the tools are registered, the failsafes are known, and the team's mandatory failsafes are included (16 §5.2). | Tests: 6 invalid card fixtures each fail with a specific error.
- [x] **T03.002** | `agents/cards.py` | `mandatory_failsafes(card)` computes the required set from team + internet + max_steps. | Tests on 4 combinations.
- [x] **T03.003** | `config/agents/_demo/demo_agent.yaml` | A demo agent card used only in tests (tools: compute, db_read_units). | Loads.

## Base agent + loop
- [x] **T03.010** | `agents/base.py` | `BaseAgent.run(ctx)` implementing lifecycle steps 1–7 (16 §2). | Tests with FakeProvider scripted sequences.
- [x] **T03.011** | `agents/base.py` | The scratchpad: observations wrapped `<observation tool="…">…</observation>`, trimmed to `settings.agents.max_observation_chars` with a trim note. | Test.
- [x] **T03.012** | `agents/base.py` | AgentAction validation: the tool must be in card.tools (else ToolNotAllowedError → counts as an invalid step, retry once, then fail). | Test.
- [x] **T03.013** | `agents/base.py` | Stores an AgentRun row with the status, failure_code, tokens, and cost. | Test.
- [x] **T03.014** | `agents/base.py` | The `postconditions()` hook; failures → retry the final output once with the reasons, then fail. | Test.
- [x] **T03.015** | `agents/base.py` | The grading hook: if the card has a rubric → call the grader's `regeneration_loop` (a stub interface now; implemented in P14). | An interface test with a stub grader.
- [x] **T03.016** | `agents/registry.py` | `get_agent(name)` → the class + card; agent classes register via a decorator. | Test.

## Tools
- [x] **T03.020** | `agents/tools/base.py` | The Tool protocol: `name`, `internet: bool`, `args_model`, `async run(args, ctx) -> Observation`. A registry. | Test.
- [x] **T03.021** | `agents/tools/web_search.py` | Wraps the SearchProvider chain (04 §7). Results ≤ 10. | respx test.
- [x] **T03.022** | `agents/tools/fetch_url.py` | Uses the research `web` fetcher (it is also built in P07; here, a minimal version with trafilatura + a cache + politeness). Returns FetchedDoc metadata + a text preview; the full text is stored in the cache by content_hash. | respx test.
- [x] **T03.023** | `agents/tools/parse_html.py` | Headings, paragraphs, and tables (via the stdlib html.parser) → structured text; a 20k-char cap. | Tests on 3 HTML fixtures.
- [x] **T03.024** | `agents/tools/parse_pdf.py` | pypdf by page range; 30-page cap. | Test on a fixture PDF.
- [x] **T03.025** | `agents/tools/parse_table.py` | HTML table / CSV / JSON → rows with inferred numeric types (handles "1,234", "12.5%", "—"); a 2000-row cap. | Tests on 6 fixtures, including messy ones.
- [x] **T03.026** | `agents/tools/compute.py` | A safe expression evaluator: an `ast` parse with a whitelist (numbers, + − × ÷, parentheses, mean/median/sum/min/max/pct_change/ratio over named row columns). Any other node → error. | Tests: valid formulas; `__import__`, attribute access, and lambdas are all rejected.
- [x] **T03.027** | `agents/tools/db_read.py` | db_read_units / evidence / findings / profile, scoped to ctx.run_id and the document; read-only. | Test: cross-run access is denied.
- [x] **T03.028** | `agents/tools/excerpt_verify.py` | Wraps citation_check (the P07 implementation; a stub now with the same signature). | Interface test.
- [x] **T03.029** | `agents/tools/structured_lookups.py` | Placeholders registering the courtlistener/openalex/crossref/google_factcheck/tmdb/openlibrary/musicbrainz/wikipedia tools that delegate to the P07 fetchers. | The registry lists them.
- [x] **T03.030** | `agents/tools/languagetool.py` | Registered here; implemented in P15. | Listed.

## Failsafes (each a module + tests)
- [x] **T03.040** | `failsafes/f01_timeout.py` | An asyncio.wait_for wrapper per tool + per agent. | Test: a slow fake tool times out → recorded.
- [x] **T03.041** | `failsafes/f02_retry.py` | tenacity policy: transient (httpx timeouts, 429, 5xx) retry up to 3 with exponential backoff + jitter; non-transient no retry. | Tests for both classes.
- [x] **T03.042** | `failsafes/f03_circuit.py` | A CircuitBreaker per key (provider/tool): closed → open after 5 failures → half-open after 60 s → closed on success. The clock is injectable for tests. | A state-machine test.
- [x] **T03.043** | `failsafes/f04_loop.py` | Detects the same (tool, args) 3 times, or 2 unchanged observation hashes in a row → LoopDetectedError → a forced degraded final. | Test.
- [x] **T03.044** | `failsafes/f05_schema.py` | Wraps validation + rejects outputs echoing the prompt or containing observation tags. | Test.
- [x] **T03.045** | `failsafes/f06_checkpoint.py` | save/load the agent state by checkpoint_key (in the `checkpoints` table; JSON). Corrupt-checkpoint detection (a hash) → restart from scratch + log. | Tests incl. corruption.
- [x] **T03.046** | `failsafes/f07_idempotency.py` | Idempotency key helper used by persist. | Test.
- [x] **T03.047** | `failsafes/f08_dead_letter.py` | `send(item, reason, inputs)`; `list()`; `retry(id)`. | Test.
- [x] **T03.048** | `failsafes/f09_watchdog.py` | Heartbeat registry + a monitor task; cancel + requeue once; the second stall → dead letter. | Test with a fake stalled agent.
- [x] **T03.049** | `failsafes/f10_budget.py` | Integrates budget slices into BaseAgent (reserve before a call, commit after). | Test: an exhausted agent slice → degraded, and team siblings continue.
- [x] **T03.050** | `failsafes/f11_degrade.py` | Degrade policy registry: per team, what "degraded" means (e.g. rewrite → no change; verify → cap MOSTLY_TRUE; audience → mark low-confidence). | Tests per policy.
- [x] **T03.051** | `failsafes/f12_sanity.py` | Empty/too long/wrong language (a simple stopword-ratio heuristic for English)/repetition/placeholder detection. | Tests.
- [x] **T03.052** | `failsafes/f13_injection.py` | A pattern list (config) of injection phrases; strips them from observations, logs, and counts. | A test fixture page with "ignore previous instructions" → stripped + logged.
- [x] **T03.053** | `failsafes/f14_politeness.py` | A per-domain token bucket (1 rps default) + a robots.txt cache + the User-Agent with CONTACT_EMAIL. | Test: the rate is respected with a fake clock.
- [x] **T03.054** | `failsafes/f15_size.py` | Byte/char/row caps with explicit truncation notes. | Test.
- [x] **T03.055** | `failsafes/f16_killswitch.py` | Checks `data/STOP` + a signal handler; `sots stop` creates the file. Agents check it between steps. | Test.
- [x] **T03.056** | `failsafes/f17_doctor.py` | `sots doctor`: config valid, cards valid, prompts present, providers healthy, tools registered, keys present (warn), disk space > 1 GB, DB `PRAGMA integrity_check`, LanguageTool reachable (warn). A colored table; exit code 1 on any hard failure. | Test with fakes.
- [x] **T03.057** | `failsafes/f18_replay.py` | `--record` stores every provider/tool response keyed by the call sequence; `--replay` serves them. | Test: record then replay → an identical AgentRun output.
- [x] **T03.058** | `failsafes/f19_canary.py` | Runs the canary fixture through a caller-supplied act function; aborts on failure. | Test.
- [x] **T03.059** | `failsafes/f20_invariants.py` | A registry of invariant checks (functions returning violations). Initial: raw files unchanged (sha256), offsets intact, every cited id exists. Teams add more in later phases. | Tests: each invariant with a planted violation.

## Events
- [x] **T03.070** | `agents/events.py` | An async pub/sub queue; event types from 16 §7; a JSONL sink to `data/logs/events.jsonl`. | Test: subscribe → receive, in order.

## Integration tests
- [x] **T03.080** | `tests/integration/test_demo_agent.py` | The demo agent: a scripted 3-step tool loop → final; kill after step 2 (kill switch) → resume → completes at step 3 with no repeated tool calls. | Passes.
- [x] **T03.081** | `tests/integration/test_failsafe_matrix.py` | A parametrized test proving each F01–F20 fires at least once. | Passes.

## Phase close
- [x] **T03.090** | — | All green; `sots doctor` passes on the dev machine (warnings allowed for keys/LanguageTool); BUILD_LOG line. | Done.
