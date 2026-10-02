"""Structured LLM calls: the only entry point for model use (P02 T02.012-T02.013).

`call_structured` implements the 9 steps of 04 §2: route → prompt → context →
cache → budget → call → parse → validate (≤2 retries, R-LLM-03) → log/cache.
Every attempt is logged to `llm_calls` (R-LLM-04); identical calls hit the
cache (R-LLM-05).
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from sots.config import Settings
from sots.errors import ValidationFailedError
from sots.providers import budget as budget_mod
from sots.providers import cache as cache_mod
from sots.providers import calllog, context_pack, prompts
from sots.providers.base import LLMProvider, LLMRequest
from sots.providers.budget import BudgetNode
from sots.providers.router import ResolvedRoute, RoutingConfig, resolve
from sots.storage.db import Connection

MAX_RETRIES = 2


def extract_json(text: str, *, strict: bool = False) -> Any:
    """First top-level JSON object/array in messy model output (T02.013).

    Strips code fences, then scans string-aware for the first `{`/`[` and its
    match. Strict mode rejects trailing non-whitespace prose.
    """
    cleaned = _strip_fences(text.strip())
    payload, rest = _scan_value(cleaned)
    if payload is None:
        raise ValueError("no JSON object or array found in model output")
    if strict and rest.strip():
        raise ValueError("trailing prose after JSON payload (strict mode)")
    return json.loads(payload)


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]
    return "\n".join(body).strip()


def _scan_value(text: str) -> tuple[str | None, str]:
    """(first top-level JSON substring, remainder) via string-aware scan."""
    start = -1
    opener = ""
    for i, char in enumerate(text):
        if char in "{[":
            start, opener = i, char
            break
    if start < 0:
        return None, text
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth == 0 and char == closer:
                return text[start : i + 1], text[i + 1 :]
            if depth == 0:
                return None, text
    return None, text


def render_input_hash(
    route: ResolvedRoute, prompt_id: str, prompt_version: int, system: str,
    user_text: str, temperature: float,
) -> str:
    """Cache/input hash over the canonical rendered call (T02.014)."""
    rendered = f"{system}\n\n{user_text}"
    return cache_mod.cache_key(
        route.provider, route.model, prompt_id, prompt_version, rendered, temperature
    )


async def call_structured[T: BaseModel](
    task: str,
    prompt_id: str,
    variables: dict[str, str],
    output_model: type[T],
    context: context_pack.ContextPack,
    run_id: str | None,
    *,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    registry: Mapping[str, LLMProvider],
    budget: BudgetNode | None = None,
    prompts_dir: str | Path = "prompts",
    prompt_version: int | None = None,
    no_cache: bool = False,
    strict_json: bool = False,
) -> T:
    """Run the 9-step structured call for `task` and return a validated model."""
    route = resolve(task, routing=routing, registry=registry)
    provider = registry[route.provider]
    template = prompts.load_prompt(prompts_dir, prompt_id, prompt_version)
    user_text = template.render(variables)
    system = context_pack.render(context)

    key = render_input_hash(
        route, template.id, template.version, system, user_text, route.temperature
    )
    if not no_cache:
        hit = cache_mod.cache_get(conn, key)
        if hit is not None:
            try:
                cached = output_model.model_validate_json(hit)
            except ValidationError:
                cached = None
            if cached is not None:
                calllog.write_call(
                    conn, run_id=run_id, task=task, provider=route.provider,
                    model=route.model, prompt_id=template.id,
                    prompt_version=template.version, input_hash=key,
                    input_tokens=0, output_tokens=0, cost_estimate=0.0,
                    latency_ms=0, status="cached", fallback_used=route.fallback_used,
                )
                return cached

    reservation = None
    if budget is not None:
        estimate_in = provider.count_tokens(system + user_text)
        est_cost = budget_mod.compute_cost(
            settings, route.provider, route.model,
            estimate_in, route.max_output_tokens,
        )
        reservation = budget.reserve(estimate_in + route.max_output_tokens, est_cost)

    schema = output_model.model_json_schema() if provider.supports_json_schema else None
    attempts = MAX_RETRIES + 1
    total_in = total_out = 0
    total_cost = 0.0
    last_error = ""
    try:
        for attempt in range(attempts):
            attempt_text = user_text
            if attempt > 0:
                attempt_text = (
                    f"{user_text}\n\nPrevious response failed validation:\n"
                    f"{last_error}\nRespond with valid JSON only."
                )
            request = LLMRequest(
                task=task, system=system,
                messages=[{"role": "user", "content": attempt_text}],
                temperature=route.temperature,
                max_output_tokens=route.max_output_tokens,
                json_schema=schema,
            )
            started = time.monotonic()
            try:
                response = await provider.complete(request)
            except Exception:
                latency_ms = int((time.monotonic() - started) * 1000)
                calllog.write_call(
                    conn, run_id=run_id, task=task, provider=route.provider,
                    model=route.model, prompt_id=template.id,
                    prompt_version=template.version, input_hash=key,
                    input_tokens=0, output_tokens=0, cost_estimate=0.0,
                    latency_ms=latency_ms, status="failed",
                    fallback_used=route.fallback_used,
                )
                raise
            latency_ms = int((time.monotonic() - started) * 1000)
            cost = budget_mod.compute_cost(
                settings, route.provider, route.model,
                response.input_tokens, response.output_tokens,
            )
            total_in += response.input_tokens
            total_out += response.output_tokens
            total_cost += cost
            try:
                payload = extract_json(response.text, strict=strict_json)
                validated = output_model.model_validate(payload)
            except (ValueError, ValidationError) as exc:
                last_error = str(exc)
                final = attempt == attempts - 1
                calllog.write_call(
                    conn, run_id=run_id, task=task, provider=route.provider,
                    model=route.model, prompt_id=template.id,
                    prompt_version=template.version, input_hash=key,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens, cost_estimate=cost,
                    latency_ms=latency_ms, status="failed" if final else "invalid_retry",
                    fallback_used=route.fallback_used,
                )
                if final:
                    raise ValidationFailedError(
                        f"{task}/{prompt_id} failed validation after "
                        f"{attempts} attempts: {last_error}"
                    ) from exc
                continue
            calllog.write_call(
                conn, run_id=run_id, task=task, provider=route.provider,
                model=route.model, prompt_id=template.id,
                prompt_version=template.version, input_hash=key,
                input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                cost_estimate=cost, latency_ms=latency_ms, status="ok",
                fallback_used=route.fallback_used,
            )
            if not no_cache:
                cache_mod.cache_put(conn, key, validated.model_dump_json())
            if reservation is not None:
                reservation.commit(total_in + total_out, total_cost)
            return validated
    except Exception:
        if reservation is not None and reservation.active:
            reservation.release()
        raise
    raise AssertionError("unreachable")  # pragma: no cover
