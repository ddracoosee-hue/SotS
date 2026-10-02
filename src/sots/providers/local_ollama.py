"""Ollama local provider over `/api/chat` (P02 T02.003-T02.004, 04 §1.2).

Cheap bulk work: segmentation, classification, summaries, safety scan,
first-pass engines. Model, `num_ctx`, and base URL come from
`settings.providers.local`; HTTP timeout uses `settings.fetch.timeout_s`
(the single HTTP timeout in settings).
"""

from __future__ import annotations

import math
from typing import Any

import httpx

from sots.errors import ProviderNotConfiguredError
from sots.providers.base import LLMRequest, LLMResponse, ProviderHealth


class OllamaProvider:
    """Async httpx client for an Ollama server (04 §1.2)."""

    name = "local"
    supports_json_schema = True  # via /api/chat `format`
    supports_web_search = False

    def __init__(
        self,
        base_url: str,
        model: str | None,
        num_ctx: int,
        context_window: int,
        timeout_s: float = 15,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self.model = model
        self.configured = bool(model)
        self._num_ctx = num_ctx
        self.context_window = context_window
        self._timeout = httpx.Timeout(timeout_s)

    def count_tokens(self, text: str) -> int:
        """Conservative estimate: ceil(len/3.5) (04 §1.2)."""
        return math.ceil(len(text) / 3.5) if text else 0

    def _require_model(self) -> str:
        if not self.model:
            raise ProviderNotConfiguredError(
                "local provider has no model; set providers.local.model (15 OI-05)"
            )
        return self.model

    async def complete(self, req: LLMRequest) -> LLMResponse:
        model = self._require_model()
        messages = [{"role": "system", "content": req.system}, *req.messages]
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": self._num_ctx,
                "temperature": req.temperature,
                "num_predict": req.max_output_tokens,
            },
        }
        if req.json_schema is not None:
            body["format"] = req.json_schema
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=body)
            response.raise_for_status()
            data = response.json()
        text = str(data.get("message", {}).get("content", ""))
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")
        in_tokens = int(input_tokens) if input_tokens is not None else self._fallback_in(req)
        out_tokens = (
            int(output_tokens) if output_tokens is not None else self.count_tokens(text)
        )
        return LLMResponse(
            text=text,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            model=str(data.get("model", model)),
            raw=data if isinstance(data, dict) else None,
        )

    def _fallback_in(self, req: LLMRequest) -> int:
        return self.count_tokens(req.system + "\n".join(m.get("content", "") for m in req.messages))

    async def health(self) -> ProviderHealth:
        """Hit `/api/tags` and confirm the configured model exists (T02.004)."""
        if not self.model:
            return ProviderHealth(name=self.name, ok=False, detail="no model configured")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # health reports, never raises
            return ProviderHealth(name=self.name, ok=False, detail=f"{type(exc).__name__}: {exc}")
        models = [m.get("name", "") for m in data.get("models", [])]
        if any(self.model == name or name.startswith(f"{self.model}:") for name in models):
            return ProviderHealth(name=self.name, ok=True, detail=f"model {self.model} found")
        return ProviderHealth(
            name=self.name, ok=False, detail=f"model {self.model} not in /api/tags"
        )
