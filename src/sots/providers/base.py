"""LLM provider protocol, request/response models (P02 T02.001, 04 §1.1).

Only code inside `providers/` may call a model API (R-LLM-01); the rest of
SotS goes through `structured.call_structured`.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict


class LLMRequest(BaseModel):
    """One model invocation (04 §1.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    system: str
    messages: list[dict]
    temperature: float
    max_output_tokens: int
    json_schema: dict | None = None


class LLMResponse(BaseModel):
    """Raw provider result, before JSON extraction (04 §1.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    input_tokens: int
    output_tokens: int
    model: str
    raw: dict | None = None


class ProviderHealth(BaseModel):
    """Health probe outcome; never raises (used by `sots settings test-providers`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    ok: bool
    detail: str


class LLMProvider(Protocol):
    """What every provider implements (04 §1.1 + model/configured/health for P02)."""

    name: str
    context_window: int
    supports_json_schema: bool
    supports_web_search: bool
    model: str | None
    configured: bool

    async def complete(self, req: LLMRequest) -> LLMResponse:
        """Run one completion; raises ProviderNotConfiguredError when unconfigured."""
        ...

    def count_tokens(self, text: str) -> int:
        """Conservative token estimate for budgeting and trimming."""
        ...

    async def health(self) -> ProviderHealth:
        """Probe readiness; reports status, never raises."""
        ...
