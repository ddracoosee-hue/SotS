"""F18 record/replay for deterministic debugging (P03 T03.057, 16 §5.1).

`--record` stores every provider/tool response keyed by call sequence;
`--replay` serves them back instead of calling anything. Serves strictly in
order: a kind/task/input mismatch or an exhausted tape raises
ReplayMismatchError. BaseAgent needs no changes: callers wrap the provider
and tool registries with the recording/replaying decorators.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from sots.agents.tools.base import Tool, ToolContext
from sots.errors import ReplayMismatchError
from sots.models.agents import Observation
from sots.providers.base import LLMProvider, LLMRequest, LLMResponse, ProviderHealth


def call_hash(task: str, system: str, messages: list[dict]) -> str:
    """Stable input hash identifying one provider call."""
    payload = json.dumps({"task": task, "system": system, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tool_hash(tool: str, args: dict[str, Any]) -> str:
    """Stable input hash identifying one tool call."""
    payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RecordStore:
    """Append-only JSONL tape of provider/tool responses."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.calls = 0

    def append(self, kind: str, key: dict[str, Any], payload: dict[str, Any]) -> None:
        """Record one response under its call key."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({"seq": self.calls, "kind": kind, "key": key, "payload": payload})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.calls += 1


class ReplayStore:
    """Serve a tape back strictly in call-sequence order."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._entries: list[dict[str, Any]] = []
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._entries.append(json.loads(line))
        self._cursor = 0

    def __len__(self) -> int:
        return len(self._entries)

    def next(self, kind: str, key: dict[str, Any]) -> dict[str, Any]:
        """Next tape entry; kind/key mismatch or exhaustion raises."""
        if self._cursor >= len(self._entries):
            raise ReplayMismatchError(f"replay tape exhausted at call {self._cursor}")
        entry = self._entries[self._cursor]
        self._cursor += 1
        if entry.get("kind") != kind or entry.get("key") != key:
            raise ReplayMismatchError(
                f"replay mismatch at call {entry.get('seq')}: "
                f"expected {kind} {key}, taped {entry.get('kind')} {entry.get('key')}"
            )
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            raise ReplayMismatchError(f"replay entry {entry.get('seq')} has no payload")
        return payload


class RecordingProvider:
    """LLMProvider decorator that tapes every response."""

    def __init__(self, inner: LLMProvider, store: RecordStore) -> None:
        self._inner = inner
        self._store = store
        self.name = inner.name
        self.context_window = inner.context_window
        self.supports_json_schema = inner.supports_json_schema
        self.supports_web_search = inner.supports_web_search
        self.model = inner.model
        self.configured = inner.configured

    async def complete(self, req: LLMRequest) -> LLMResponse:
        response = await self._inner.complete(req)
        self._store.append(
            "provider",
            {"task": req.task, "hash": call_hash(req.task, req.system, req.messages)},
            response.model_dump(mode="json"),
        )
        return response

    def count_tokens(self, text: str) -> int:
        return self._inner.count_tokens(text)

    async def health(self) -> ProviderHealth:
        return await self._inner.health()


class ReplayingProvider:
    """LLMProvider decorator that serves the tape (calls nothing)."""

    def __init__(self, store: ReplayStore, *, name: str, model: str | None) -> None:
        self._store = store
        self.name = name
        self.context_window = 0
        self.supports_json_schema = True
        self.supports_web_search = False
        self.model = model
        self.configured = True

    async def complete(self, req: LLMRequest) -> LLMResponse:
        payload = self._store.next(
            "provider",
            {"task": req.task, "hash": call_hash(req.task, req.system, req.messages)},
        )
        return LLMResponse.model_validate(payload)

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4) if text else 0

    async def health(self) -> ProviderHealth:
        return ProviderHealth(name=self.name, ok=True, detail="replay tape")


class RecordingTool:
    """Tool decorator that tapes every observation."""

    def __init__(self, inner: Tool[Any], store: RecordStore) -> None:
        self._inner = inner
        self._store = store
        self.name = inner.name
        self.internet = inner.internet
        self.args_model = inner.args_model

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        observation = await self._inner.run(args, ctx)
        self._store.append(
            "tool",
            {"tool": self.name, "hash": tool_hash(self.name, args.model_dump(mode="json"))},
            observation.model_dump(mode="json"),
        )
        return observation


class ReplayingTool:
    """Tool decorator that serves the tape (executes nothing)."""

    def __init__(
        self, name: str, internet: bool, args_model: type[BaseModel], store: ReplayStore
    ) -> None:
        self.name = name
        self.internet = internet
        self.args_model = args_model
        self._store = store

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        _ = ctx
        payload = self._store.next(
            "tool", {"tool": self.name, "hash": tool_hash(self.name, args.model_dump(mode="json"))}
        )
        return Observation.model_validate(payload)
