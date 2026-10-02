"""P03 agent card tests (T03.001-T03.003, 16 §1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

import sots.agents.tools  # noqa: F401 (register every tool)
from sots.agents.cards import load_cards, mandatory_failsafes
from sots.agents.tools.base import registered_tools
from sots.errors import ConfigError
from sots.providers.router import RoutingConfig, RoutingTask, load_routing

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

BASE_CARD: dict[str, Any] = {
    "name": "demo_agent",
    "team": "fact_check",
    "role": "test-only card",
    "prompts": {
        "system": "_demo/demo.system.v1.md",
        "step": "_demo/demo.step.v1.md",
    },
    "output_model": "test output",
    "routing_task": "classify.unit",
    "tools": ["compute", "db_read_units"],
    "internet": False,
    "limits": {"max_steps": 3, "max_tokens": 60000, "timeout_s": 600, "max_retries": 2},
    "grading": {"rubric": None},
    "failsafes": [
        "F01", "F02", "F04", "F05", "F06", "F07",
        "F08", "F09", "F10", "F12", "F16", "F20",
    ],
    "on_failure": "dead_letter",
}


def _routing() -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={
            "classify.unit": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=600
            )
        },
    )


def _prompts(tmp_path: Path) -> Path:
    root = tmp_path / "prompts"
    (root / "_demo").mkdir(parents=True)
    (root / "_demo" / "demo.system.v1.md").write_text("system", encoding="utf-8")
    (root / "_demo" / "demo.step.v1.md").write_text("step", encoding="utf-8")
    return root


def _write_card(cards_dir: Path, filename: str, **overrides: Any) -> Path:
    card = {**BASE_CARD, **overrides}
    path = cards_dir / filename
    path.write_text(yaml.safe_dump(card), encoding="utf-8")
    return path


def _load(cards_dir: Path, prompts_dir: Path) -> dict:
    return load_cards(
        cards_dir, prompts_dir=prompts_dir, routing=_routing(),
        tools=registered_tools(),
    )


def test_valid_card_loads(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "demo.yaml")
    cards = _load(cards_dir, _prompts(tmp_path))
    assert list(cards) == ["demo_agent"]
    assert cards["demo_agent"].team == "fact_check"


def test_unparseable_card(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    (cards_dir / "bad.yaml").write_text("{[not yaml", encoding="utf-8")
    with pytest.raises(ConfigError, match="cannot parse"):
        _load(cards_dir, _prompts(tmp_path))


def test_non_mapping_card(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    (cards_dir / "list.yaml").write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="must parse to a mapping"):
        _load(cards_dir, _prompts(tmp_path))


def test_invalid_model_card(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    card = {k: v for k, v in BASE_CARD.items() if k != "tools"}
    (cards_dir / "model.yaml").write_text(yaml.safe_dump(card), encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid agent card"):
        _load(cards_dir, _prompts(tmp_path))


def test_non_snake_case_name(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "name.yaml", name="DemoAgent")
    with pytest.raises(ConfigError, match="non-snake_case"):
        _load(cards_dir, _prompts(tmp_path))


def test_missing_prompt_files(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(
        cards_dir, "prompts.yaml",
        prompts={"system": "_demo/demo.system.v1.md", "step": "nope/missing.v1.md"},
    )
    with pytest.raises(ConfigError, match="missing prompt files"):
        _load(cards_dir, _prompts(tmp_path))


def test_unknown_routing_task(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "routing.yaml", routing_task="nope.task")
    with pytest.raises(ConfigError, match="unknown routing task"):
        _load(cards_dir, _prompts(tmp_path))


def test_unregistered_tool(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "tools.yaml", tools=["compute", "nope_tool"])
    with pytest.raises(ConfigError, match="unregistered tools"):
        _load(cards_dir, _prompts(tmp_path))


def test_missing_mandatory_failsafes(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "failsafes.yaml", failsafes=["F01"])
    with pytest.raises(ConfigError, match="missing mandatory failsafes"):
        _load(cards_dir, _prompts(tmp_path))


def test_duplicate_card_name(tmp_path: Path) -> None:
    cards_dir = tmp_path / "agents"
    cards_dir.mkdir()
    _write_card(cards_dir, "a.yaml")
    _write_card(cards_dir, "b.yaml")
    with pytest.raises(ConfigError, match="duplicate agent card name"):
        _load(cards_dir, _prompts(tmp_path))


def test_mandatory_failsafes_combinations() -> None:
    base = {
        "F01", "F02", "F05", "F06", "F07", "F08",
        "F10", "F12", "F16", "F20",
    }
    assert mandatory_failsafes("fact_check", False, 1) == frozenset(base)
    assert mandatory_failsafes("fact_check", True, 1) == frozenset(
        base | {"F03", "F13", "F14", "F15"}
    )
    assert mandatory_failsafes("legal_chamber", False, 1) == frozenset(
        base | {"F09"}
    )
    assert mandatory_failsafes("rewrite_pass_a", False, 3) == frozenset(
        base | {"F04", "F09", "F11"}
    )


def test_demo_card_loads() -> None:
    """T03.003: the real demo card validates against the real tree."""
    cards = load_cards(
        CONFIG_DIR / "agents",
        prompts_dir=PROMPTS_DIR,
        routing=load_routing(CONFIG_DIR / "routing.yaml"),
        tools=registered_tools(),
    )
    assert "demo_agent" in cards
    assert cards["demo_agent"].tools == ["compute", "db_read_units"]
