# P02 — Providers

**Prerequisites:** P01. **Blueprint refs:** 04 (all), 01 §B.

## Protocol + implementations
- [x] **T02.001** | `providers/base.py` | LLMRequest, LLMResponse, the LLMProvider Protocol (04 §1.1). | Pyright accepts FakeProvider as an LLMProvider.
- [x] **T02.002** | `providers/fake.py` | FakeProvider: loads fixtures from `tests/fixtures/llm/<task>/*.json`; matches on (task, input_hash), falling back to (task, "default"); records the requests; can script sequences (a list of responses per key) for multi-step agents; can inject failures (exceptions, invalid JSON, delays). | Tests for each mode.
- [x] **T02.003** | `providers/local_ollama.py` | httpx async client to `/api/chat`; passes `format` = JSON schema when given; `num_ctx` + temperature from routing; parses token counts from the response; timeouts from settings. | respx-mocked test for the request shape + response parsing.
- [x] **T02.004** | `providers/local_ollama.py` | `count_tokens` = ceil(len/3.5). `health()` hits `/api/tags` and checks the model exists. | Tests.
- [x] **T02.005** | `providers/muse.py` | A configurable adapter: base_url, auth header name/format, request/response field mapping, and model names, all from `settings.providers.muse` (OI-03). If the config is incomplete → ProviderNotConfiguredError. Include `supports_json_schema`, `supports_web_search`, `context_window` from config. **No hard-coded API shape.** | Test: incomplete config raises; a complete *fake* config + respx works end-to-end.
- [x] **T02.006** | `providers/muse.py` | A docstring block listing exactly which config fields the author must fill in (mirrors OI-03). | Present.

## Routing, structured calls, cache, budget
- [x] **T02.010** | `providers/router.py` | `resolve(task) -> (provider, model, params)` from routing.yaml; fallback_order; records `fallback_used`. | Tests: normal; fallback; unknown task → ConfigError.
- [x] **T02.011** | `providers/prompts.py` | A prompt loader: reads `prompts/<id>.v<N>.md`, parses the front-matter header (`id`, `version`, `variables`, `output_model`), fills with string.Template, and checks every declared variable is provided. | Tests: a missing variable raises; an unknown variable raises.
- [x] **T02.012** | `providers/structured.py` | `call_structured(...)` implementing the 9 steps of 04 §2 (render → cache → budget → call → parse → validate → retry ≤ 2 with the error appended → log → cache). | Tests: happy path; invalid→valid on retry 1; always invalid → ValidationFailedError + 3 llm_calls rows.
- [x] **T02.013** | `providers/structured.py` | The JSON extractor: strips code fences, takes the first top-level JSON object/array, and rejects trailing prose if strict. | Tests on 8 messy output fixtures.
- [x] **T02.014** | `providers/cache.py` | Key = sha256(provider, model, prompt_id, version, rendered_input, temperature). Stored in the `cache` table with the output + created_at. Bypass flag `--no-cache`. | Tests: hit/miss/bypass.
- [x] **T02.015** | `providers/budget.py` | A Budget tree (run → act → team → agent slices) with `reserve(tokens)` / `commit(actual)` / `release()`; costs from the price table in settings; warn at 80%; raise at 100%. | Tests: nested slice exhaustion stops only that slice.
- [x] **T02.016** | `providers/budget.py` | `estimate(task, n_items)` for dry runs (average prompt size per task from the prompt file length + context budgets). | Test: deterministic estimate on a fixture.
- [x] **T02.017** | `providers/calllog.py` | Writes an LLMCall row per attempt, with status ok/cached/invalid_retry/failed. | Test.

## Context packs + summary integration
- [x] **T02.020** | `providers/context_pack.py` | The ContextPack builder: the pieces + priorities + budgets (04 §4), with the `TASK_PIECES` map for every routing task (including the new teams: rewrite.* uses the Style Guide as a piece; legal.* uses issue context; audience.persona_read uses the persona card + journey spec). | Test: never exceeds the budget.
- [x] **T02.021** | `providers/context_pack.py` | Sentence-safe trimming: fall back to the summary; never cut mid-sentence. | A property test (hypothesis-free: 200 randomized cases with the stdlib `random` + a fixed seed).
- [x] **T02.022** | `providers/context_pack.py` | Budget scaling by the provider context window (04 §4). | Test.

## CLI
- [x] **T02.030** | `cli.py` | `sots settings test-providers` → a table of provider health (local ✔/✘, muse ✔/✘/not configured). | Manual + a unit test with fakes.
- [x] **T02.031** | `cli.py` | `sots cost [--since]` reads llm_calls → a table by task/provider. | Test.

## Phase close
- [x] **T02.090** | — | All green; BUILD_LOG line. | Done.
