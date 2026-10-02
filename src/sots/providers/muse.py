"""Muse API adapter, fully config-driven (P02 T02.005-T02.006, 04 §1).

The Muse endpoint, auth, model names, and request/response shapes are unknown
(15 OI-03), so this adapter has **no hard-coded API shape**: everything comes
from `settings.providers.muse`. Until the author fills it in, `complete()`
raises `ProviderNotConfiguredError` and the router falls back to local (04 §3).

Author: fill in these `settings.yaml → providers.muse` fields (mirrors OI-03):
  base_url, model, context_window, price_input_per_1k, price_output_per_1k,
  supports_json_schema, supports_web_search, request_path, auth_header,
  auth_scheme, request_template, response_text_path, plus the optional
  response_input_tokens_path, response_output_tokens_path, response_model_path.
Set the secret itself in `.env` as MUSE_API_KEY (never in YAML).

`request_template` is the request body with `$placeholders`: `$model`,
`$messages` (the full message list), `$temperature`, `$max_tokens`, and
optionally `$json_schema` (used only when the request carries a schema and
`supports_json_schema` is true; otherwise it renders as null). A placeholder
that is the whole string value is replaced with the object; anywhere else it
is string-interpolated.
Response paths are dot paths (`choices.0.message.content`) into the
response JSON; integer segments index into lists.
"""

from __future__ import annotations

import math
import string
from typing import Any

import httpx

from sots.config import MuseProviderSettings
from sots.errors import ConfigError, ProviderNotConfiguredError
from sots.providers.base import LLMRequest, LLMResponse, ProviderHealth


def _walk_path(data: Any, dot_path: str) -> Any:
    """Extract `a.0.b` from nested dicts/lists; None when anything is missing."""
    current = data
    for segment in dot_path.split("."):
        if isinstance(current, list):
            if not segment.isdigit() or int(segment) >= len(current):
                return None
            current = current[int(segment)]
        elif isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
        else:
            return None
    return current


def render_template(template: Any, values: dict[str, Any]) -> Any:
    """Substitute `$placeholders` in a template (whole-value keeps the object)."""
    if isinstance(template, dict):
        return {key: render_template(val, values) for key, val in template.items()}
    if isinstance(template, list):
        return [render_template(val, values) for val in template]
    if isinstance(template, str):
        if template in values:
            return values[template]
        return string.Template(template).safe_substitute(
            {k.lstrip("$"): v for k, v in values.items()}
        )
    return template


class MuseProvider:
    """Config-driven Muse adapter; raises until the author configures it."""

    name = "muse"

    def __init__(self, settings: MuseProviderSettings, api_key: str | None) -> None:
        self._settings = settings
        self._api_key = api_key
        self.model = settings.model
        self.context_window = settings.context_window or 0
        self.supports_json_schema = bool(settings.supports_json_schema)
        self.supports_web_search = bool(settings.supports_web_search)
        self.configured = not self._missing(settings, api_key)

    @staticmethod
    def _missing(settings: MuseProviderSettings, api_key: str | None) -> list[str]:
        missing: list[str] = []
        if not settings.base_url:
            missing.append("base_url")
        if not api_key:
            missing.append("MUSE_API_KEY")
        if not settings.model:
            missing.append("model")
        if not settings.context_window:
            missing.append("context_window")
        if not settings.request_path:
            missing.append("request_path")
        if not settings.request_template:
            missing.append("request_template")
        if not settings.response_text_path:
            missing.append("response_text_path")
        return missing

    def missing_fields(self) -> list[str]:
        """Required config still empty (also used by health/detail messages)."""
        return self._missing(self._settings, self._api_key)

    def count_tokens(self, text: str) -> int:
        """Rough estimate (unknown tokenizer): ceil(len/4)."""
        return math.ceil(len(text) / 4) if text else 0

    def _require_configured(self) -> None:
        missing = self.missing_fields()
        if missing:
            raise ProviderNotConfiguredError(
                "muse provider is not configured; the author must set "
                f"{', '.join(missing)} (15 OI-03)"
            )

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self._require_configured()
        settings = self._settings
        assert settings.base_url and settings.model and settings.request_path
        assert settings.request_template and settings.response_text_path
        messages = [{"role": "system", "content": req.system}, *req.messages]
        values: dict[str, Any] = {
            "$model": settings.model,
            "$messages": messages,
            "$temperature": req.temperature,
            "$max_tokens": req.max_output_tokens,
        }
        if req.json_schema is not None and settings.supports_json_schema:
            values["$json_schema"] = req.json_schema
        else:
            values["$json_schema"] = None
        body = render_template(dict(settings.request_template), values)
        auth_value = (
            f"{settings.auth_scheme} {self._api_key}"
            if settings.auth_scheme
            else str(self._api_key)
        )
        headers = {settings.auth_header: auth_value}
        url = settings.base_url.rstrip("/") + settings.request_path
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        text = _walk_path(data, settings.response_text_path)
        if text is None:
            raise ConfigError(
                "muse response has no text at "
                f"'{settings.response_text_path}'; check the response mapping"
            )
        text = str(text)
        return LLMResponse(
            text=text,
            input_tokens=self._tokens(data, settings.response_input_tokens_path, req, True),
            output_tokens=self._tokens(data, settings.response_output_tokens_path, req, False),
            model=self._model_name(data, settings),
            raw=data if isinstance(data, dict) else None,
        )

    def _tokens(
        self, data: Any, dot_path: str | None, req: LLMRequest, is_input: bool
    ) -> int:
        if dot_path:
            value = _walk_path(data, dot_path)
            if value is not None:
                return int(value)
        if is_input:
            joined = req.system + "\n".join(m.get("content", "") for m in req.messages)
            return self.count_tokens(joined)
        return self.count_tokens(str(_walk_path(data, self._settings.response_text_path or "")))

    def _model_name(self, data: Any, settings: MuseProviderSettings) -> str:
        if settings.response_model_path:
            value = _walk_path(data, settings.response_model_path)
            if value is not None:
                return str(value)
        return str(settings.model)

    async def health(self) -> ProviderHealth:
        missing = self.missing_fields()
        if missing:
            return ProviderHealth(
                name=self.name, ok=False, detail=f"not configured: {', '.join(missing)}"
            )
        return ProviderHealth(
            name=self.name,
            ok=True,
            detail="configured (no live probe: API shape is author-defined)",
        )
