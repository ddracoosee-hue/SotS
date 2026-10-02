"""P02 service tests (T02.011-T02.017, T02.020-T02.022, T02.030-T02.031)."""

from __future__ import annotations

import logging
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
import yaml
from pydantic import BaseModel
from typer.testing import CliRunner

from sots.cli import app
from sots.config import load_settings
from sots.errors import (
    BudgetExceededError,
    ConfigError,
    ValidationFailedError,
)
from sots.models.cache import CacheEntry
from sots.models.run import LLMCall
from sots.providers import budget as budget_mod
from sots.providers import calllog
from sots.providers.budget import BudgetNode, Reservation, create_run_budget
from sots.providers.cache import cache_get, cache_key, cache_put
from sots.providers.calllog import CostRow
from sots.providers.context_pack import (
    TASK_PIECES,
    ContextPack,
    ContextSources,
    PieceInput,
    build,
    pack_tokens,
    render,
    scale_factor,
    trim_to_budget,
)
from sots.providers.fake import FakeProvider
from sots.providers.prompts import PromptTemplate, available_versions, load_prompt
from sots.providers.router import RoutingConfig, RoutingTask, load_routing
from sots.providers.structured import call_structured, extract_json
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

runner = CliRunner()
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _write_prompt(
    prompts_dir: Path,
    prompt_id: str = "verify/skeptic",
    version: int = 1,
    variables: list[str] | None = None,
    body: str = "Judge this unit: $unit_text",
) -> Path:
    path = prompts_dir / f"{prompt_id}.v{version}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = {
        "id": prompt_id,
        "version": version,
        "variables": variables if variables is not None else ["unit_text"],
        "output_model": "SkepticReading",
    }
    path.write_text(f"---\n{yaml.safe_dump(header)}---\n{body}\n", encoding="utf-8")
    return path


class _Reading(BaseModel):
    verdict: str
    confidence: float


def _pack(system: str = "You are a skeptic.") -> ContextPack:
    return ContextPack(task="verify.skeptic", system_role=system, pieces=[])


def _db(tmp_path: Path) -> Any:
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    return conn


def _routing(task: str = "verify.skeptic", provider: str = "fake") -> RoutingConfig:
    return RoutingConfig(
        fallback_order=["muse", "local", "fake"],
        tasks={task: RoutingTask(provider=provider, temperature=0.0, max_output_tokens=50)},
    )


# --- T02.011: prompt loader ---


def test_prompt_load_render_and_versions(tmp_path: Path) -> None:
    _write_prompt(tmp_path, version=1)
    _write_prompt(tmp_path, version=2, body="Second: $unit_text")
    assert available_versions(tmp_path, "verify/skeptic") == [1, 2]
    assert available_versions(tmp_path, "nope/none") == []
    latest = load_prompt(tmp_path, "verify/skeptic")
    assert isinstance(latest, PromptTemplate)
    assert (latest.version, latest.output_model) == (2, "SkepticReading")
    assert latest.render({"unit_text": "X"}) == "Second: X\n"
    first = load_prompt(tmp_path, "verify/skeptic", 1)
    assert first.render({"unit_text": "X"}) == "Judge this unit: X\n"


def test_prompt_variable_checks(tmp_path: Path) -> None:
    _write_prompt(tmp_path)
    template = load_prompt(tmp_path, "verify/skeptic", 1)
    with pytest.raises(ConfigError, match="missing variables: unit_text"):
        template.render({})
    with pytest.raises(ConfigError, match="undeclared variables: extra"):
        template.render({"unit_text": "x", "extra": "y"})


def test_prompt_header_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no prompt file"):
        load_prompt(tmp_path, "ghost/ghost")
    _write_prompt(tmp_path)
    with pytest.raises(ConfigError, match="not found"):
        load_prompt(tmp_path, "verify/skeptic", 9)
    bad_id = tmp_path / "bad.v1.md"
    bad_id.write_text("---\nid: other\nversion: 1\nvariables: []\noutput_model: M\n---\nbody\n")
    with pytest.raises(ConfigError, match="header id"):
        load_prompt(tmp_path, "bad")
    bad_vars = tmp_path / "vars.v1.md"
    bad_vars.write_text("---\nid: vars\nversion: 1\nvariables: x\noutput_model: M\n---\nbody\n")
    with pytest.raises(ConfigError, match="'variables' must be a string list"):
        load_prompt(tmp_path, "vars")
    no_body = tmp_path / "empty.v1.md"
    no_body.write_text("---\nid: empty\nversion: 1\nvariables: []\noutput_model: M\n---\n   \n")
    with pytest.raises(ConfigError, match="empty body"):
        load_prompt(tmp_path, "empty")
    no_header = tmp_path / "plain.v1.md"
    no_header.write_text("just prose\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="must start with"):
        load_prompt(tmp_path, "plain")


# --- T02.012: structured calls ---


async def test_structured_happy_path_logs_and_caches(tmp_path: Path) -> None:
    _write_prompt(tmp_path / "prompts")
    fake = FakeProvider()
    fake.script_default("verify.skeptic", [{"text": '{"verdict": "true", "confidence": 0.9}'}])
    conn = _db(tmp_path)
    try:
        settings = load_settings(CONFIG_DIR, env_file=None)
        result = await call_structured(
            "verify.skeptic", "verify/skeptic", {"unit_text": "Water is wet."}, _Reading,
            _pack(), "run_1", conn=conn, settings=settings, routing=_routing(),
            registry={"fake": fake}, prompts_dir=tmp_path / "prompts",
        )
        assert result == _Reading(verdict="true", confidence=0.9)
        rows = storage_repo.list_llm_calls(conn)
        assert len(rows) == 1
        assert rows[0].status == "ok" and rows[0].fallback_used is False
        assert rows[0].prompt_version == 1 and rows[0].run_id == "run_1"
        # Second identical call is a cache hit: no new provider call.
        again = await call_structured(
            "verify.skeptic", "verify/skeptic", {"unit_text": "Water is wet."}, _Reading,
            _pack(), "run_1", conn=conn, settings=settings, routing=_routing(),
            registry={"fake": fake}, prompts_dir=tmp_path / "prompts",
        )
        assert again == result
        assert len(fake.calls) == 1
        assert [r.status for r in storage_repo.list_llm_calls(conn)] == ["ok", "cached"]
    finally:
        conn.close()


async def test_structured_retry_then_success_and_total_failure(tmp_path: Path) -> None:
    _write_prompt(tmp_path / "prompts")
    settings = load_settings(CONFIG_DIR, env_file=None)
    kwargs: dict[str, Any] = {
        "conn": None, "settings": settings, "routing": _routing(),
        "prompts_dir": tmp_path / "prompts",
    }
    conn = _db(tmp_path)
    try:
        kwargs["conn"] = conn
        flaky = FakeProvider()
        flaky.script_default("verify.skeptic", [
            {"text": "not json"}, {"text": '{"verdict": "false", "confidence": 0.5}'},
        ])
        result = await call_structured(
            "verify.skeptic", "verify/skeptic", {"unit_text": "u"}, _Reading,
            _pack(), None, registry={"fake": flaky}, **kwargs,
        )
        assert result.verdict == "false"
        assert [r.status for r in storage_repo.list_llm_calls(conn)] == ["invalid_retry", "ok"]
        # Retry prompt carries the validation error.
        assert "Previous response failed validation" in flaky.calls[1].messages[0]["content"]

        hopeless = FakeProvider()
        hopeless.script_default("verify.skeptic", [{"text": "still not json"}])
        with pytest.raises(ValidationFailedError, match="3 attempts"):
            await call_structured(
                "verify.skeptic", "verify/skeptic", {"unit_text": "v"}, _Reading,
                _pack(), None, registry={"fake": hopeless}, **kwargs,
            )
        statuses = [r.status for r in storage_repo.list_llm_calls(conn)]
        assert statuses[-3:] == ["invalid_retry", "invalid_retry", "failed"]
    finally:
        conn.close()


async def test_structured_no_cache_bypass_and_budget_and_errors(tmp_path: Path) -> None:
    _write_prompt(tmp_path / "prompts")
    settings = load_settings(CONFIG_DIR, env_file=None)
    conn = _db(tmp_path)
    try:
        fake = FakeProvider()
        fake.script_default("verify.skeptic", [{"text": '{"verdict": "v", "confidence": 1}'}])
        base: dict[str, Any] = {
            "conn": conn, "settings": settings, "routing": _routing(),
            "registry": {"fake": fake}, "prompts_dir": tmp_path / "prompts",
        }
        await call_structured("verify.skeptic", "verify/skeptic", {"unit_text": "u"},
                              _Reading, _pack(), None, **base)
        await call_structured("verify.skeptic", "verify/skeptic", {"unit_text": "u"},
                              _Reading, _pack(), None, no_cache=True, **base)
        assert len(fake.calls) == 2  # bypass skips read AND write
        tiny = BudgetNode("run", 5)
        with pytest.raises(BudgetExceededError, match="slice 'run'"):
            # Fresh input (a cache hit would rightly skip the budget check).
            await call_structured("verify.skeptic", "verify/skeptic", {"unit_text": "budget-probe"},
                                  _Reading, _pack(), None, budget=tiny, **base)
        with pytest.raises(ConfigError, match="unknown routing task"):
            await call_structured("ghost.task", "verify/skeptic", {"unit_text": "u"},
                                  _Reading, _pack(), None, **base)
        with pytest.raises(ConfigError, match="no prompt file"):
            await call_structured("verify.skeptic", "ghost/prompt", {"unit_text": "u"},
                                  _Reading, _pack(), None, **base)
        exploding = FakeProvider()
        exploding.script_default("verify.skeptic", [RuntimeError("provider down")])
        with pytest.raises(RuntimeError, match="provider down"):
            await call_structured(
                "verify.skeptic", "verify/skeptic", {"unit_text": "w"}, _Reading,
                _pack(), None, conn=conn, settings=settings, routing=_routing(),
                registry={"fake": exploding}, prompts_dir=tmp_path / "prompts",
            )
        assert storage_repo.list_llm_calls(conn)[-1].status == "failed"
    finally:
        conn.close()


async def test_structured_records_fallback(tmp_path: Path) -> None:
    _write_prompt(tmp_path / "prompts")
    settings = load_settings(CONFIG_DIR, env_file=None)
    routing = RoutingConfig(
        fallback_order=["fake"],
        tasks={
            "verify.skeptic": RoutingTask(provider="muse", temperature=0.0, max_output_tokens=9)
        },
    )
    fake = FakeProvider()
    fake.script_default("verify.skeptic", [{"text": '{"verdict": "v", "confidence": 1}'}])
    conn = _db(tmp_path)
    try:
        await call_structured(
            "verify.skeptic", "verify/skeptic", {"unit_text": "u"}, _Reading,
            _pack(), None, conn=conn, settings=settings, routing=routing,
            registry={"fake": fake}, prompts_dir=tmp_path / "prompts",
        )
        row = storage_repo.list_llm_calls(conn)[0]
        assert (row.provider, row.fallback_used) == ("fake", True)
    finally:
        conn.close()


# --- T02.013: JSON extractor ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('```\n{"a": 1}\n```', {"a": 1}),
        ('Here is my analysis: {"a": 1}', {"a": 1}),
        ('{"a": 1} Hope that helps!', {"a": 1}),
        ('[1, {"a": [2, 3]}]', [1, {"a": [2, 3]}]),
        (r'{"q": "braces { in \"strings\" }"}', {"q": 'braces { in "strings" }'}),
        ('{"first": 1} {"second": 2}', {"first": 1}),
    ],
)
def test_extract_json_messy_fixtures(raw: str, expected: Any) -> None:
    assert extract_json(raw) == expected


def test_extract_json_strict_and_missing() -> None:
    assert extract_json('{"a": 1} trailing', strict=False) == {"a": 1}
    with pytest.raises(ValueError, match="strict mode"):
        extract_json('{"a": 1} trailing', strict=True)
    assert extract_json('{"a": 1}   ', strict=True) == {"a": 1}
    with pytest.raises(ValueError, match="no JSON"):
        extract_json("nothing but prose")
    with pytest.raises(ValueError, match="no JSON"):
        extract_json('{"unclosed": true')


# --- T02.014: cache ---


def test_cache_key_deterministic_and_sensitive() -> None:
    key = cache_key("local", "m", "p", 1, "input", 0.0)
    assert key == cache_key("local", "m", "p", 1, "input", 0.0)
    assert len(key) == 64
    assert cache_key("muse", "m", "p", 1, "input", 0.0) != key
    assert cache_key("local", "m", "p", 2, "input", 0.0) != key
    assert cache_key("local", "m", "p", 1, "other", 0.0) != key
    assert cache_key("local", "m", "p", 1, "input", 0.5) != key


def test_cache_hit_miss_and_expiry(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    try:
        assert cache_get(conn, "k") is None
        cache_put(conn, "k", '{"a": 1}')
        assert cache_get(conn, "k") == '{"a": 1}'
        cache_put(conn, "k", '{"a": 2}')
        assert cache_get(conn, "k") == '{"a": 2}'
        storage_repo.save_cache_entry(
            conn,
            CacheEntry(
                key="old", value="v", created_at=datetime(2020, 1, 1),
                expires_at=datetime(2020, 1, 2),
            ),
        )
        assert cache_get(conn, "old") is None
    finally:
        conn.close()


# --- T02.015-T02.016: budget ---


def test_budget_reserve_commit_release() -> None:
    root = BudgetNode("run", 100, 1.0)
    reservation = root.reserve(40, 0.4)
    assert isinstance(reservation, Reservation) and reservation.active
    assert (root.reserved_tokens, root.used_tokens) == (40, 0)
    reservation.commit(30, 0.3)
    assert (root.reserved_tokens, root.used_tokens, root.used_cost) == (0, 30, 0.3)
    assert reservation.active is False
    with pytest.raises(ValueError, match="already settled"):
        reservation.release()
    second = root.reserve(10)
    second.release()
    assert (root.reserved_tokens, root.used_tokens) == (0, 30)
    with pytest.raises(ValueError, match="negative"):
        root.reserve(-1)
    with pytest.raises(ValueError, match="negative"):
        root.reserve(1).commit(-2)


def test_budget_nested_exhaustion_isolates_slices() -> None:
    root = BudgetNode("run", 100)
    left = root.new_child("left", 10)
    right = root.new_child("right", 90)
    with pytest.raises(BudgetExceededError, match=r"slice 'run\.left'"):
        left.reserve(11)
    assert (left.reserved_tokens, root.reserved_tokens) == (0, 0)
    right.reserve(90).commit(90)
    assert right.used_tokens == 90 and left.used_tokens == 0
    # Parent cap binds even when the child has room; the child keeps its room.
    root2 = BudgetNode("run", 100)
    filler = root2.new_child("filler", 100)
    worker = root2.new_child("worker", 100)
    filler.reserve(95).commit(95)
    with pytest.raises(BudgetExceededError, match="slice 'run'"):
        worker.reserve(6)
    assert (worker.reserved_tokens, worker.used_tokens) == (0, 0)
    worker.reserve(5).commit(5)
    assert worker.used_tokens == 5
    with pytest.raises(ValueError, match="already exists"):
        root.new_child("left", 5)


def test_budget_cost_cap_and_warnings(caplog: pytest.LogCaptureFixture) -> None:
    root = BudgetNode("run", 1000, 1.0)
    with pytest.raises(BudgetExceededError, match="cost budget"):
        root.reserve(10, 1.5)
    with caplog.at_level(logging.WARNING, logger="sots.providers.budget"):
        root.reserve(800)
    assert "80% used" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="sots.providers.budget"):
        root.reserve(10)
    assert "80% used" not in caplog.text  # warned once


def test_compute_cost_and_run_budget() -> None:
    settings = load_settings(CONFIG_DIR, env_file=None)
    assert budget_mod.compute_cost(settings, "local", "m", 1000, 1000) == 0.0
    assert budget_mod.compute_cost(settings, "unknown", "m", 1, 1) == 0.0
    assert budget_mod.compute_cost(settings, "muse", "m", 1, 1) == 0.0  # prices unset
    root = create_run_budget(settings)
    assert (root.name, root.max_tokens, root.max_cost) == ("run", 2000000, None)


def test_estimate_deterministic(tmp_path: Path) -> None:
    body = "Classify the unit: $unit_text"
    _write_prompt(tmp_path, "classify/unit", body=body)
    settings = load_settings(CONFIG_DIR, env_file=None)
    counter = lambda text: len(text) // 4  # noqa: E731
    pieces = {"classify.unit": ["book_profile", "neighbours"]}
    per_item = len(body + "\n") // 4 + 600 + 1500
    assert (
        budget_mod.estimate(
            "classify.unit", 3, prompts_dir=tmp_path, task_pieces=pieces,
            budgets=settings.context.budgets, counter=counter,
            prompt_id="classify/unit",
        )
        == per_item * 3
    )
    with pytest.raises(ValueError, match="no context pieces"):
        budget_mod.estimate("ghost.task", 1, prompts_dir=tmp_path, task_pieces=pieces,
                            budgets=settings.context.budgets, counter=counter)


# --- T02.017: call log ---


def test_write_call_and_summarize(tmp_path: Path) -> None:
    conn = _db(tmp_path)
    try:
        calllog.write_call(
            conn, run_id="r1", task="classify.unit", provider="local", model="m",
            prompt_id="classify/unit", prompt_version=1, input_hash="h",
            input_tokens=10, output_tokens=5, cost_estimate=0.0, latency_ms=12,
            status="ok",
        )
        calllog.write_call(
            conn, run_id="r1", task="classify.unit", provider="local", model="m",
            prompt_id="classify/unit", prompt_version=1, input_hash="h2",
            input_tokens=20, output_tokens=5, cost_estimate=0.0, latency_ms=9,
            status="cached",
        )
        rows = storage_repo.list_llm_calls(conn)
        assert isinstance(rows[0], LLMCall) and rows[0].input_hash == "h"
        summary = calllog.summarize(conn)
        assert summary == [
            CostRow(task="classify.unit", provider="local", calls=2,
                    input_tokens=30, output_tokens=10, cost=0.0)
        ]
        assert calllog.summarize(conn, datetime(2030, 1, 1)) == []
        assert len(calllog.summarize(conn, datetime(2000, 1, 1))) == 1
    finally:
        conn.close()


# --- T02.020-T02.022: context packs ---


def test_task_pieces_cover_routing() -> None:
    routing = load_routing(CONFIG_DIR / "routing.yaml")
    assert set(TASK_PIECES) == set(routing.tasks)
    assert all(pieces for pieces in TASK_PIECES.values())
    for task, pieces in TASK_PIECES.items():
        if task.startswith("rewrite."):
            assert "style_guide" in pieces, task
        if task.startswith("legal."):
            assert "issue_context" in pieces, task
    # R-FOUND-01 (T04A.021): content tasks lead with F1 + F2.
    assert TASK_PIECES["classify.unit"] == [
        "f1_book", "f2_chapter", "book_profile", "chapter_brief", "neighbours",
    ]
    assert TASK_PIECES["audience.persona_read"] == [
        "f1_book", "f2_chapter", "book_profile", "chapter_brief",
        "persona_card", "journey_spec", "neighbours",
    ]


def test_build_never_exceeds_budget() -> None:
    settings = load_settings(CONFIG_DIR, env_file=None)
    budgets = settings.context.budgets
    counter = lambda text: max(1, len(text) // 4) if text else 0  # noqa: E731
    sources = ContextSources(
        system_role="Role.",
        book_profile=PieceInput(text="short book"),
        chapter_brief=PieceInput(text="x" * 20000, summary="brief summary"),
        neighbours=PieceInput(text="y" * 30000, summary="z" * 20000),
    )
    pack = build("classify.unit", sources, budgets=budgets, context_window=32000, counter=counter)
    assert pack.system_role == "Role."
    total_budget = 0
    for piece in pack.pieces:
        assert counter(piece.text) <= piece.budget
        total_budget += piece.budget
    assert pack_tokens(pack, counter) <= total_budget + counter("Role.")
    by_name = {p.name: p for p in pack.pieces}
    assert by_name["book_profile"].truncated is False
    assert by_name["chapter_brief"].text == "brief summary"
    assert by_name["neighbours"].truncated is True
    assert render(pack).startswith("Role.\n\n## Book profile\nshort book")
    with pytest.raises(ConfigError, match="no context pieces"):
        build("ghost.task", sources, budgets=budgets, context_window=32000, counter=counter)


def test_trim_to_budget_sentence_safe_property() -> None:
    rng = random.Random(20260214)
    words = ["alpha", "beta", "gamma", "delta", "eps", "zeta", "eta", "theta"]
    splitter = re.compile(r"(?<=[.!?])\s+")
    for _ in range(200):
        sentences = [
            " ".join(rng.choice(words) for _ in range(rng.randint(1, 12)))
            + rng.choice([".", "!", "?"])
            for _ in range(rng.randint(1, 8))
        ]
        text = " ".join(sentences)
        budget = rng.randint(0, len(text) + 10)
        trimmed = trim_to_budget(text, budget, len)
        assert len(trimmed) <= budget
        if not trimmed:
            continue
        input_sentences = [s for s in splitter.split(text.strip()) if s]
        out_sentences = [s for s in splitter.split(trimmed) if s]
        assert out_sentences == input_sentences[: len(out_sentences)]
        assert text.startswith(out_sentences[0])
    assert trim_to_budget("", 10, len) == ""
    assert trim_to_budget("   ", 10, len) == ""
    assert trim_to_budget("one sentence.", 100, len) == "one sentence."
    assert trim_to_budget("Too long for zero.", 0, len) == ""


def test_scale_factor_and_window_scaling() -> None:
    assert scale_factor(32000) == 1.0
    assert scale_factor(16000) == 0.5
    assert scale_factor(128000) == 4.0
    assert scale_factor(1000000) == 4.0
    with pytest.raises(ValueError, match="positive"):
        scale_factor(0)
    settings = load_settings(CONFIG_DIR, env_file=None)
    pack = build(
        "classify.unit", ContextSources(), budgets=settings.context.budgets,
        context_window=64000, counter=len,
    )
    by_name = {p.name: p for p in pack.pieces}
    assert by_name["book_profile"].budget == 1200
    assert by_name["neighbours"].budget == 3000


def test_context_models_round_trip() -> None:
    sources = ContextSources(book_profile=PieceInput(text="t", summary="s"))
    assert ContextSources.model_validate(sources.model_dump()) == sources
    pack = ContextPack(task="t", system_role="r", pieces=[])
    assert ContextPack.model_validate(pack.model_dump()) == pack


# --- T02.030-T02.031: CLI ---


def test_cli_test_providers_unconfigured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.chdir(tmp_path)
    shutil.copytree(CONFIG_DIR, tmp_path / "config")
    result = runner.invoke(app, ["settings", "test-providers"])
    assert result.exit_code == 0, result.output
    assert "not configured" in result.output
    assert "local" in result.output and "muse" in result.output


@respx.mock
def test_cli_test_providers_with_fakes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.chdir(tmp_path)
    shutil.copytree(CONFIG_DIR, tmp_path / "config")
    raw = yaml.safe_load((tmp_path / "config/settings.yaml").read_text(encoding="utf-8"))
    raw["providers"]["local"]["base_url"] = "http://fake-ollama:11434"
    raw["providers"]["local"]["model"] = "test-model"
    (tmp_path / "config/settings.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    respx.get("http://fake-ollama:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "test-model:latest"}]})
    )
    result = runner.invoke(app, ["settings", "test-providers"])
    assert result.exit_code == 0, result.output
    assert "ok" in result.output


def test_cli_cost_table_and_filters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.chdir(tmp_path)
    shutil.copytree(CONFIG_DIR, tmp_path / "config")
    (tmp_path / "data").mkdir()
    conn = storage_db.connect(tmp_path / "data/sots.db")
    storage_db.migrate(conn)
    calllog.write_call(
        conn, run_id="r", task="classify.unit", provider="local", model="m",
        prompt_id="p", prompt_version=1, input_hash="h", input_tokens=100,
        output_tokens=50, cost_estimate=0.25, latency_ms=5, status="ok",
    )
    conn.close()
    result = runner.invoke(app, ["cost"])
    assert result.exit_code == 0, result.output
    assert "classify.unit" in result.output and "0.2500" in result.output
    assert "total cost: 0.2500" in result.output
    filtered = runner.invoke(app, ["cost", "--since", "2030-01-01"])
    assert filtered.exit_code == 0
    assert "no LLM calls recorded" in filtered.output
    bad_date = runner.invoke(app, ["cost", "--since", "yesterday"])
    assert bad_date.exit_code == 1
    missing_config = runner.invoke(app, ["cost", "--root", str(tmp_path / "empty")])
    assert missing_config.exit_code == 1
    (tmp_path / "nodb" / "config").mkdir(parents=True)
    shutil.copy(CONFIG_DIR / "settings.yaml", tmp_path / "nodb/config/settings.yaml")
    missing_db = runner.invoke(app, ["cost", "--root", str(tmp_path / "nodb")])
    assert missing_db.exit_code == 1
    assert "no database" in missing_db.output
