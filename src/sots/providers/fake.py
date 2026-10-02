"""Deterministic test provider (P02 T02.002, 04 §1).

Canned JSON keyed by `(task, input_hash)` from
`tests/fixtures/llm/<task>/<hash>.json`, falling back to `<task>/default.json`.
Records every request; scripts multi-response sequences; injects failures
(exceptions, invalid JSON, delays) for retry and resilience tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from sots.providers.base import LLMProvider, LLMRequest, LLMResponse, ProviderHealth


def fixture_input_hash(task: str, system: str, messages: list[dict]) -> str:
    """Stable key for fixture lookup: sha256 over task + rendered input."""
    payload = json.dumps(
        {"task": task, "system": system, "messages": messages}, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FakeProvider:
    """Test-only provider (R-CODE-07: tests use this, never a real API)."""

    name = "fake"
    context_window = 128000
    supports_json_schema = True
    supports_web_search = False
    model: str | None = "fake"
    configured = True

    def __init__(self, fixtures_dir: str | Path | None = None) -> None:
        self._fixtures = Path(fixtures_dir) if fixtures_dir else None
        self.calls: list[LLMRequest] = []
        self._scripts: dict[tuple[str, str], list[Any]] = {}

    def count_tokens(self, text: str) -> int:
        return math.ceil(len(text) / 4) if text else 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(name=self.name, ok=True, detail="test provider")

    def script(self, task: str, input_hash: str, responses: list[Any]) -> None:
        """Queue responses per key; each item is a response dict or an Exception.

        Response dicts take `text` plus optional `input_tokens`,
        `output_tokens`, and `delay_s`. After the queue drains, the last item
        repeats so multi-step agents stay deterministic.
        """
        self._scripts[(task, input_hash)] = list(responses)

    def script_default(self, task: str, responses: list[Any]) -> None:
        """Queue responses for a task regardless of input hash."""
        self._scripts[(task, "*")] = list(responses)

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        item = self._next_scripted(req)
        if isinstance(item, BaseException):
            raise item
        if item is None:
            item = self._load_fixture(req)
        if not isinstance(item, dict):
            raise ValueError(f"fake script item must be a dict or Exception, got {item!r}")
        delay = item.get("delay_s", 0)
        if delay:
            await asyncio.sleep(float(delay))
        text = str(item.get("text", ""))
        return LLMResponse(
            text=text,
            input_tokens=int(item.get("input_tokens", self._request_tokens(req))),
            output_tokens=int(item.get("output_tokens", self.count_tokens(text))),
            model="fake",
            raw={"task": req.task},
        )

    def _next_scripted(self, req: LLMRequest) -> Any:
        key = (req.task, fixture_input_hash(req.task, req.system, req.messages))
        for lookup in (key, (req.task, "*")):
            queue = self._scripts.get(lookup)
            if not queue:
                continue
            if len(queue) > 1:
                return queue.pop(0)
            return queue[0]
        return None

    def _request_tokens(self, req: LLMRequest) -> int:
        rendered = req.system + "\n" + json.dumps(req.messages, sort_keys=True)
        return self.count_tokens(rendered)

    def _load_fixture(self, req: LLMRequest) -> dict[str, Any]:
        if self._fixtures is None:
            raise FileNotFoundError(
                f"fake provider has no fixtures dir and no script for task {req.task!r}; "
                "pass fixtures_dir or use script()/script_default()"
            )
        digest = fixture_input_hash(req.task, req.system, req.messages)
        candidates = [
            self._fixtures / req.task / f"{digest}.json",
            self._fixtures / req.task / "default.json",
        ]
        for path in candidates:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(f"fake fixture {path} must be a JSON object")
                return data
        searched = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(f"no fake fixture for task {req.task!r}; searched {searched}")


def _as_provider(provider: LLMProvider) -> LLMProvider:
    """Static assertion (T02.001): FakeProvider satisfies LLMProvider."""
    return provider


_PROTOCOL_CHECK: LLMProvider = _as_provider(FakeProvider())
