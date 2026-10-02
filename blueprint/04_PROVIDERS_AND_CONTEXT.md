# 04 — PROVIDERS AND LARGE-CONTEXT HANDLING

## 1. Providers

There are two real providers and one test provider.

| Provider | File | Role |
|----------|------|------|
| `muse` | `providers/muse.py` | Heavy reasoning: research planning, verification, media interpretation, shadow, synthesis. |
| `local` | `providers/local_ollama.py` | Cheap bulk work: segmentation, classification, summaries, safety scan, first-pass engines. |
| `fake` | `providers/fake.py` | Tests only. Returns canned JSON keyed by `(task, input_hash)`. |

> **The Muse API adapter is intentionally left open.** Its endpoint, auth, model names,
> context window, pricing, and tool/web-search support are unknown and will be defined by
> the author. Build `muse.py` against the `LLMProvider` protocol below. Put every
> Muse-specific value in `config/settings.yaml → providers.muse` and `.env`, never in
> code. Until the details are given, `muse.py` raises `ProviderNotConfiguredError`, and
> the router falls back as described in §3.

### 1.1 Protocol (`providers/base.py`)

```python
class LLMRequest(BaseModel):
    task: str
    system: str
    messages: list[dict]          # [{"role": "user"|"assistant", "content": str}]
    temperature: float
    max_output_tokens: int
    json_schema: dict | None      # the output model's JSON schema, if the provider supports it

class LLMResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    raw: dict | None = None

class LLMProvider(Protocol):
    name: str
    context_window: int           # tokens, from config
    supports_json_schema: bool
    supports_web_search: bool
    async def complete(self, req: LLMRequest) -> LLMResponse: ...
    def count_tokens(self, text: str) -> int: ...
```

### 1.2 Local provider (Ollama)

- Endpoint: `settings.yaml → providers.local.base_url` (default `http://localhost:11434`).
- Use `/api/chat` with `format: <json schema>` whenever a schema is given.
- The model name and `num_ctx` come from config. Suggested defaults (the author confirms
  them against their hardware): an instruction-tuned 7–14B model with `num_ctx: 32768`.
- `count_tokens`: approximately `len(text) / 3.5`, rounded up (a conservative estimate).

## 2. Structured calls (`providers/structured.py`)

This is the **only** function the rest of the code uses to call an LLM:

```python
async def call_structured(
    task: str,                   # routing key
    prompt_id: str,              # e.g. "verify/skeptic"
    variables: dict[str, str],   # filled into the prompt template
    output_model: type[T],
    context: ContextPack,
    run_id: str | None,
) -> T
```

The steps, in order:
1. Look up `task` in `routing.yaml` → provider, model, temperature, max_output_tokens.
2. Load the prompt file. Check its version header. Fill in the variables with
   `string.Template` (`$name` syntax only).
3. Render the context pack (§4) into the system message.
4. Hash the full input. If it is in the cache, return the cached result (R-LLM-05).
5. Check the budget (§5). If it would be exceeded, raise `BudgetExceededError`.
6. Call the provider.
7. Parse the JSON (strip code fences if present) and validate it with `output_model`.
8. If invalid, retry up to 2 times with the validation error appended (R-LLM-03).
9. Log to `llm_calls` (R-LLM-04). Store in the cache. Return.

## 3. Routing (`config/routing.yaml`)

```yaml
defaults:
  fallback_order: [muse, local]     # used when the preferred provider is not configured
tasks:
  summarize.chunk:        {provider: local, temperature: 0.0, max_output_tokens: 800}
  segment.extract_units:  {provider: local, temperature: 0.0, max_output_tokens: 4000}
  classify.unit:          {provider: local, temperature: 0.0, max_output_tokens: 600}
  classify.safety_scan:   {provider: local, temperature: 0.0, max_output_tokens: 200}
  research.plan_queries:  {provider: muse,  temperature: 0.0, max_output_tokens: 800}
  verify.researcher:      {provider: muse,  temperature: 0.0, max_output_tokens: 2000}
  verify.skeptic:         {provider: muse,  temperature: 0.0, max_output_tokens: 1500}
  verify.adjudicator:     {provider: muse,  temperature: 0.0, max_output_tokens: 1500}
  media.identify:         {provider: local, temperature: 0.0, max_output_tokens: 300}
  media.check:            {provider: muse,  temperature: 0.0, max_output_tokens: 2500}
  psyche.emotion:         {provider: local, temperature: 0.2, max_output_tokens: 1500}
  psyche.cognitive:       {provider: muse,  temperature: 0.2, max_output_tokens: 1500}
  psyche.theme:           {provider: muse,  temperature: 0.2, max_output_tokens: 1500}
  psyche.archetype:       {provider: muse,  temperature: 0.3, max_output_tokens: 1500}
  psyche.blindspot:       {provider: muse,  temperature: 0.3, max_output_tokens: 1500}
  psyche.reader:          {provider: muse,  temperature: 0.5, max_output_tokens: 1500}
  psyche.synthesize:      {provider: muse,  temperature: 0.2, max_output_tokens: 2000}
  narrative.map_messages: {provider: local, temperature: 0.0, max_output_tokens: 2000}
  narrative.voice:        {provider: muse,  temperature: 0.2, max_output_tokens: 1200}
  shadow.reflect:         {provider: muse,  temperature: 0.7, max_output_tokens: 3000}
  shadow.grade:           {provider: muse,  temperature: 0.0, max_output_tokens: 2000}
```

- If a task's provider is not configured, use `fallback_order`. Record the fallback in
  the `LLMCall` row and show it in the report ("verified with local model: lower
  reliability").
- Verification tasks (`verify.*`) that fall back to `local` have the final verdict capped
  at `MOSTLY_TRUE`, and the report flags them.

## 4. Context packs (`providers/context_pack.py`)

Every call gets a **Context Pack**: a budgeted block of standing context placed before the
task-specific input.

Assembly order (highest priority first). Stop adding pieces when the budget is used up:

| Priority | Piece | Source | Default budget |
|---|---|---|---|
| 1 | System role + rules summary for the task | prompt file | — |
| 2 | Book profile (premise, reader, promise) | `profile/book.md` | 600 tok |
| 3 | Current chapter brief | `profile/chapters/<id>_brief.md` | 800 tok |
| 4 | Core messages (book + chapter) | `profile/messages.yaml` | 400 tok |
| 5 | Author profile (compressed) | `profile/author.md` | 400 tok |
| 6 | Document summary (from the summary tree) | stage 2 | 800 tok |
| 7 | Neighbouring units (±N around the target) | DB | 1500 tok |
| 8 | Relevant supplement excerpts | `supplements/` | 1500 tok |

- Each task declares which pieces it needs, in `context_pack.TASK_PIECES`.
  Example: `classify.unit` uses 1, 2, 3, 7. `shadow.reflect` uses 1–6.
- The piece budgets live in `settings.yaml → context.budgets`, and are scaled up when the
  provider's `context_window` is larger (budget × min(4, context_window / 32000)).
- If a piece is over its budget, use its summarized version. **Never cut text mid-sentence.**

## 5. Large inputs: the summary tree and map-reduce

Word vomits can be very long (100k+ words). No stage may assume the document fits into
one call.

1. **Chunking** (`segment/chunker.py`): split on paragraph boundaries into chunks of
   `settings.chunk.target_tokens` (local: 3000, muse: 12000), with `overlap_tokens: 200`.
   Never split inside a sentence.
2. **Summary tree** (`segment/summarizer.py`):
   - Level 0: one summary per chunk (≤ 200 words).
   - Level 1: groups of 8 chunk summaries → one summary.
   - Repeat until a single root summary remains.
   - Stored in the `summaries` table with `(document_id, level, index, text, child_ids)`.
3. **Whole-document stages** (theme, drift, shadow) receive: the root summary + the level-1
   summaries + the specific units they are judging. They never receive the whole raw text.
4. **Per-unit stages** (classify, verify, media) receive one unit, its neighbours, and a
   context pack.
5. **Deduplication across overlaps**: when two units from overlapping chunks have
   overlapping `[start_char, end_char)` ranges with a text similarity ≥ 90, keep the one
   from the earlier chunk.

## 6. Budget and cost (`providers/budget.py`)

- `settings.yaml → budget.max_tokens_per_run` (default 2,000,000) and
  `budget.max_cost_per_run` (currency, default: left for the author to set).
- `sots run --dry-run` estimates the tokens per stage without calling any model, using
  unit counts × average prompt sizes, and prints a table.
- When 80% of the budget is used, log a warning and show it in the TUI. At 100%, the
  current stage finishes its in-flight calls and the run stops with status `FAILED`
  (reason `budget`). The run can be resumed after raising the budget.
- Prices per 1k tokens for each provider and model live in config. Local costs 0.

## 7. Web search provider

Search is separate from the LLM providers (`research/search/`):

```python
class SearchProvider(Protocol):
    name: str
    async def search(self, query: str, max_results: int) -> list[SearchHit]: ...

class SearchHit(BaseModel):
    url: str; title: str; snippet: str; rank: int
```

Implementations (the enabled ones are listed in `settings.yaml → search.providers`, in order):
- `muse_search.py`: only if the Muse API offers search (open item).
- `searxng.py`: a self-hosted SearXNG instance (free, local-friendly).
- `tavily.py`: a hosted search API (needs a key).

A snippet from a search hit is **never** used as evidence. It only decides which URLs to
fetch. Evidence always comes from fetched page text (R-TRUTH-02).
