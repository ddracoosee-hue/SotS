"""P02 provider tests (T02.001-T02.006, T02.010): protocol, fake, ollama, muse, router."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from sots.config import MuseProviderSettings, Settings, load_settings
from sots.errors import ConfigError, ProviderNotConfiguredError
from sots.models.cache import CacheEntry
from sots.models.run import LLMCall
from sots.providers import muse as muse_module
from sots.providers.base import LLMProvider, LLMRequest
from sots.providers.fake import FakeProvider, fixture_input_hash
from sots.providers.local_ollama import OllamaProvider
from sots.providers.muse import MuseProvider, render_template
from sots.providers.router import (
    ResolvedRoute,
    RoutingConfig,
    RoutingTask,
    build_registry,
    load_routing,
    resolve,
)
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
FIXTURES_LLM = Path(__file__).resolve().parents[1] / "fixtures" / "llm"


def _req(task: str = "classify.unit", system: str = "sys") -> LLMRequest:
    return LLMRequest(
        task=task,
        system=system,
        messages=[{"role": "user", "content": "hello"}],
        temperature=0.0,
        max_output_tokens=100,
        json_schema=None,
    )


# --- T02.001: protocol ---


def test_protocol_members_present() -> None:
    provider: LLMProvider = FakeProvider()
    assert provider.name == "fake"
    assert provider.context_window > 0
    assert provider.configured is True
    assert callable(provider.complete)
    assert callable(provider.count_tokens)
    assert callable(provider.health)


def test_request_response_defaults() -> None:
    req = _req()
    assert req.json_schema is None
    assert req.model_dump()["temperature"] == 0.0


# --- T02.002: fake modes ---


async def test_fake_loads_committed_fixture() -> None:
    provider = FakeProvider(FIXTURES_LLM)
    response = await provider.complete(_req())
    assert json.loads(response.text)["content_type"] == "factual_claim"
    assert response.output_tokens == 12
    assert provider.calls == [_req()]


async def test_fake_prefers_hash_fixture_over_default(tmp_path: Path) -> None:
    task_dir = tmp_path / "verify.skeptic"
    task_dir.mkdir(parents=True)
    (task_dir / "default.json").write_text('{"text": "fallback"}', encoding="utf-8")
    req = _req("verify.skeptic")
    digest = fixture_input_hash(req.task, req.system, req.messages)
    (task_dir / f"{digest}.json").write_text('{"text": "exact"}', encoding="utf-8")
    provider = FakeProvider(tmp_path)
    assert (await provider.complete(req)).text == "exact"


async def test_fake_missing_fixture_raises(tmp_path: Path) -> None:
    provider = FakeProvider(tmp_path)
    with pytest.raises(FileNotFoundError, match="no fake fixture"):
        await provider.complete(_req("nothing.here"))
    with pytest.raises(FileNotFoundError, match="no fixtures dir"):
        await FakeProvider().complete(_req())


async def test_fake_script_sequence_repeats_last() -> None:
    provider = FakeProvider()
    provider.script_default("classify.unit", [{"text": "one"}, {"text": "two"}])
    assert (await provider.complete(_req())).text == "one"
    assert (await provider.complete(_req())).text == "two"
    assert (await provider.complete(_req())).text == "two"
    assert len(provider.calls) == 3


async def test_fake_script_hash_specific_beats_default() -> None:
    provider = FakeProvider()
    req = _req()
    digest = fixture_input_hash(req.task, req.system, req.messages)
    provider.script_default(req.task, [{"text": "default"}])
    provider.script(req.task, digest, [{"text": "specific"}])
    assert (await provider.complete(req)).text == "specific"


async def test_fake_injects_exceptions_invalid_json_and_delays() -> None:
    import time

    provider = FakeProvider()
    provider.script_default("boom.task", [ValueError("kaput")])
    with pytest.raises(ValueError, match="kaput"):
        await provider.complete(_req("boom.task"))
    provider.script_default("raw.task", [{"text": "not json at all"}])
    assert (await provider.complete(_req("raw.task"))).text == "not json at all"
    provider.script_default("slow.task", [{"text": "{}", "delay_s": 0.05}])
    started = time.monotonic()
    await provider.complete(_req("slow.task"))
    assert time.monotonic() - started >= 0.04


def test_fake_count_tokens() -> None:
    provider = FakeProvider()
    assert provider.count_tokens("") == 0
    assert provider.count_tokens("abcd") == 1
    assert provider.count_tokens("abcde") == 2
    assert provider.count_tokens("x" * 100) == math.ceil(100 / 4)


async def test_fake_health() -> None:
    health = await FakeProvider().health()
    assert (health.name, health.ok) == ("fake", True)


# --- T02.003-T02.004: ollama ---


@respx.mock
async def test_ollama_request_shape_and_parsing() -> None:
    route = respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "qwen3:14b",
                "message": {"role": "assistant", "content": '{"a": 1}'},
                "prompt_eval_count": 40,
                "eval_count": 9,
            },
        )
    )
    provider = OllamaProvider("http://ollama:11434", "qwen3:14b", 32768, 32768)
    req = LLMRequest(
        task="classify.unit", system="sys", messages=[{"role": "user", "content": "hi"}],
        temperature=0.2, max_output_tokens=600, json_schema={"type": "object"},
    )
    response = await provider.complete(req)
    assert route.called
    body = json.loads(route.calls[0].request.content.decode())
    assert body["model"] == "qwen3:14b"
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["format"] == {"type": "object"}
    assert body["options"] == {"num_ctx": 32768, "temperature": 0.2, "num_predict": 600}
    assert (response.text, response.input_tokens, response.output_tokens) == ('{"a": 1}', 40, 9)
    assert response.model == "qwen3:14b"


@respx.mock
async def test_ollama_no_format_without_schema_and_token_fallback() -> None:
    route = respx.post("http://o:11434/api/chat").mock(
        return_value=httpx.Response(
            200, json={"message": {"content": "plain"}, "model": "m"}
        )
    )
    provider = OllamaProvider("http://o:11434/", "m", 4096, 4096)
    response = await provider.complete(_req())
    assert "format" not in json.loads(route.calls[0].request.content.decode())
    assert response.input_tokens == provider.count_tokens("syshello")
    assert response.output_tokens == provider.count_tokens("plain")


async def test_ollama_unconfigured_raises() -> None:
    provider = OllamaProvider("http://o:11434", None, 4096, 4096)
    assert provider.configured is False
    with pytest.raises(ProviderNotConfiguredError, match="OI-05"):
        await provider.complete(_req())


def test_ollama_count_tokens() -> None:
    provider = OllamaProvider("http://o:11434", "m", 4096, 4096)
    assert provider.count_tokens("") == 0
    assert provider.count_tokens("abcd") == 2
    assert provider.count_tokens("x" * 35) == 10


@respx.mock
async def test_ollama_health_found_missing_and_error() -> None:
    respx.get("http://o:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen3:14b"}]})
    )
    ok_provider = OllamaProvider("http://o:11434", "qwen3:14b", 1, 1)
    health = await ok_provider.health()
    assert health.ok and "found" in health.detail
    tagged = OllamaProvider("http://o:11434", "qwen3", 1, 1)
    assert (await tagged.health()).ok is True  # bare name matches the tagged install
    missing = OllamaProvider("http://o:11434", "nope:1b", 1, 1)
    assert (await missing.health()).ok is False
    down = OllamaProvider("http://down:11434", "m", 1, 1, timeout_s=0.01)
    respx.get("http://down:11434/api/tags").mock(side_effect=httpx.ConnectError("down"))
    assert (await down.health()).ok is False
    assert (await OllamaProvider("http://o:11434", None, 1, 1).health()).ok is False


# --- T02.005-T02.006: muse ---


def _muse_settings(**overrides: Any) -> MuseProviderSettings:
    base: dict[str, Any] = {
        "base_url": "https://muse.test",
        "api_key_env": "MUSE_API_KEY",
        "model": "muse-large",
        "context_window": 200000,
        "supports_json_schema": True,
        "supports_web_search": False,
        "price_input_per_1k": 0.01,
        "price_output_per_1k": 0.03,
        "request_path": "/v1/generate",
        "auth_header": "Authorization",
        "auth_scheme": "Bearer",
        "request_template": {
            "model": "$model",
            "input": "$messages",
            "temp": "$temperature",
            "max": "$max_tokens",
            "schema": "$json_schema",
        },
        "response_text_path": "output.text",
        "response_input_tokens_path": "usage.in",
        "response_output_tokens_path": "usage.out",
        "response_model_path": "model",
    }
    base.update(overrides)
    return MuseProviderSettings.model_validate(base)


async def test_muse_incomplete_config_raises() -> None:
    provider = MuseProvider(_muse_settings(base_url=None, model=None), None)
    assert provider.configured is False
    assert provider.missing_fields() == ["base_url", "MUSE_API_KEY", "model"]
    with pytest.raises(ProviderNotConfiguredError, match=r"base_url.*model"):
        await provider.complete(_req())
    health = await provider.health()
    assert health.ok is False and "base_url" in health.detail


@respx.mock
async def test_muse_complete_config_end_to_end() -> None:
    route = respx.post("https://muse.test/v1/generate").mock(
        return_value=httpx.Response(
            200,
            json={
                "output": {"text": '{"ok": true}'},
                "usage": {"in": 11, "out": 4},
                "model": "muse-large",
            },
        )
    )
    provider = MuseProvider(_muse_settings(), "sekret")
    assert provider.configured is True
    req = LLMRequest(
        task="verify.skeptic", system="sys", messages=[{"role": "user", "content": "q"}],
        temperature=0.0, max_output_tokens=50, json_schema={"type": "object"},
    )
    response = await provider.complete(req)
    assert route.called
    sent = route.calls[0].request
    assert sent.headers["Authorization"] == "Bearer sekret"
    body = json.loads(sent.content.decode())
    assert body["model"] == "muse-large"
    assert body["input"][0] == {"role": "system", "content": "sys"}
    assert body["schema"] == {"type": "object"}
    assert (response.text, response.input_tokens, response.output_tokens) == ('{"ok": true}', 11, 4)
    assert response.model == "muse-large"
    assert (await provider.health()).ok is True


@respx.mock
async def test_muse_token_fallback_and_missing_text() -> None:
    respx.post("https://muse.test/v1/generate").mock(
        return_value=httpx.Response(200, json={"output": {"text": "hi"}})
    )
    bare = _muse_settings(
        response_input_tokens_path=None, response_output_tokens_path=None,
        response_model_path=None,
    )
    provider = MuseProvider(bare, "k")
    response = await provider.complete(_req())
    assert response.input_tokens == provider.count_tokens("syshello")
    assert response.output_tokens == provider.count_tokens("hi")
    assert response.model == "muse-large"
    broken = MuseProvider(_muse_settings(response_text_path="nope.missing"), "k")
    with pytest.raises(ConfigError, match=r"nope\.missing"):
        await broken.complete(_req())


def test_render_template_shapes() -> None:
    values: dict[str, Any] = {"$model": "m", "$messages": [{"role": "user"}], "$n": 3}
    assert render_template("$messages", values) == [{"role": "user"}]
    assert render_template("model=$model n=$n", values) == "model=m n=3"
    assert render_template({"a": ["$model", 1]}, values) == {"a": ["m", 1]}
    assert render_template(7, values) == 7


def test_muse_docstring_lists_config_fields() -> None:
    doc = muse_module.__doc__ or ""
    for field in (
        "base_url", "model", "context_window", "price_input_per_1k",
        "price_output_per_1k", "supports_json_schema", "supports_web_search",
        "request_path", "auth_header", "auth_scheme", "request_template",
        "response_text_path", "MUSE_API_KEY",
    ):
        assert field in doc


def test_muse_count_tokens() -> None:
    provider = MuseProvider(_muse_settings(), "k")
    assert provider.count_tokens("") == 0
    assert provider.count_tokens("abcd") == 1


# --- T02.010: router ---


def _routing(**tasks: dict[str, Any]) -> RoutingConfig:
    return RoutingConfig(
        fallback_order=["muse", "local"],
        tasks={name: RoutingTask.model_validate(entry) for name, entry in tasks.items()},
    )


def _settings() -> Settings:
    return load_settings(CONFIG_DIR, env_file=None)


def test_resolve_normal_and_unknown_task() -> None:
    routing = load_routing(CONFIG_DIR / "routing.yaml")
    registry = {"local": OllamaProvider("http://o", "m", 1, 1), "fake": FakeProvider()}
    route = resolve("classify.unit", routing=routing, registry=registry)
    assert isinstance(route, ResolvedRoute)
    assert (route.provider, route.model, route.fallback_used) == ("local", "m", False)
    assert route.temperature == 0.0
    assert route.max_output_tokens == 600
    with pytest.raises(ConfigError, match="unknown routing task"):
        resolve("nope.task", routing=routing, registry=registry)


def test_resolve_fallback_records_it() -> None:
    routing = _routing(
        **{"verify.skeptic": {"provider": "muse", "temperature": 0.0, "max_output_tokens": 9}}
    )
    registry = {
        "muse": MuseProvider(_muse_settings(base_url=None), None),
        "local": OllamaProvider("http://o", "m", 1, 1),
    }
    route = resolve("verify.skeptic", routing=routing, registry=registry)
    assert (route.provider, route.fallback_used, route.preferred_provider) == (
        "local",
        True,
        "muse",
    )


def test_resolve_none_configured_raises() -> None:
    routing = _routing(**{"a.b": {"provider": "muse", "temperature": 0.0, "max_output_tokens": 1}})
    registry = {
        "muse": MuseProvider(_muse_settings(base_url=None), None),
        "local": OllamaProvider("http://o", None, 1, 1),
    }
    with pytest.raises(ProviderNotConfiguredError, match="no configured provider"):
        resolve("a.b", routing=routing, registry=registry)


def test_resolve_supports_fake_registry() -> None:
    routing = _routing(**{"t.t": {"provider": "fake", "temperature": 0.5, "max_output_tokens": 7}})
    route = resolve("t.t", routing=routing, registry={"fake": FakeProvider()})
    assert (route.provider, route.model, route.temperature) == ("fake", "fake", 0.5)


def test_load_routing_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_routing(tmp_path / "missing.yaml")
    bad = tmp_path / "routing.yaml"
    bad.write_text("tasks: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="cannot parse"):
        load_routing(bad)
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="must parse to a mapping"):
        load_routing(bad)


def test_build_registry_from_settings() -> None:
    registry = build_registry(_settings())
    assert set(registry) == {"local", "muse"}
    assert registry["local"].configured is False  # no local model in stock config
    assert registry["muse"].configured is False


# --- P02 storage: fallback column + cache table ---


def test_migration_002_adds_fallback_used(tmp_path: Path) -> None:
    db_path = tmp_path / "m.db"
    conn = storage_db.connect(db_path)
    try:
        applied = storage_db.migrate(conn)
        assert applied[:2] == [1, 2]  # later migrations may follow
        assert storage_db.migrate(conn) == []
        cols = [r["name"] for r in conn.execute('PRAGMA table_info("llm_calls")')]
        assert "fallback_used" in cols
    finally:
        conn.close()


def test_llm_call_fallback_round_trip(tmp_path: Path) -> None:
    from datetime import datetime

    conn = storage_db.connect(tmp_path / "c.db")
    storage_db.migrate(conn)
    try:
        call = LLMCall(
            id="call_1", run_id="run_1", task="t", provider="local", model="m",
            prompt_id="p", prompt_version=1, input_hash="h", input_tokens=1,
            output_tokens=2, cost_estimate=0.0, latency_ms=3, status="ok",
            created_at=datetime(2026, 1, 1), fallback_used=True,
        )
        storage_repo.save_llm_call(conn, call)
        assert storage_repo.get_llm_call(conn, "call_1") == call
    finally:
        conn.close()


def test_cache_entry_round_trip(tmp_path: Path) -> None:
    from datetime import datetime

    conn = storage_db.connect(tmp_path / "c.db")
    storage_db.migrate(conn)
    try:
        entry = CacheEntry(key="k", value="v", created_at=datetime(2026, 1, 1))
        assert storage_repo.get_cache_entry(conn, "k") is None
        storage_repo.save_cache_entry(conn, entry)
        assert storage_repo.get_cache_entry(conn, "k") == entry
        assert storage_repo.count_cache_entries(conn) == 1
    finally:
        conn.close()


def test_settings_loads_new_p02_keys() -> None:
    settings = _settings()
    assert settings.providers.muse.request_path is None
    assert settings.providers.muse.auth_scheme == "Bearer"
    assert settings.context.budgets.style_guide == 600
    assert settings.context.budgets.journey_spec == 400


def test_routing_yaml_loads() -> None:
    routing = load_routing(CONFIG_DIR / "routing.yaml")
    assert routing.fallback_order == ["muse", "local"]
    assert len(routing.tasks) == 66
    assert routing.tasks["shadow.reflect"].temperature == 0.7
    assert routing.tasks["foundation.parse_brief"].max_output_tokens == 8000
    assert routing.tasks["classify.block_map"].provider == "local"


def test_prompt_loader_rejects_bad_yaml(tmp_path: Path) -> None:
    prompt = tmp_path / "x.v1.md"
    prompt.write_text("---\n[sorry\n---\nbody\n", encoding="utf-8")
    from sots.providers import prompts as prompt_loader

    with pytest.raises(ConfigError, match="invalid prompt header"):
        prompt_loader.load_prompt(tmp_path, "x")
