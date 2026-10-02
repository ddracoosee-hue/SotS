"""P00 slice D (T00.040-T00.043): core errors, settings, logging, writer stub."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from sots import logging_setup
from sots.config import Settings, load_settings
from sots.errors import ConfigError, SotsError, WriterDisabledError
from sots.writer import draft

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def test_valid_settings_load_from_config() -> None:
    settings = load_settings(CONFIG_DIR, env_file=None)
    assert isinstance(settings, Settings)
    assert settings.paths.db_path == "data/sots.db"
    assert settings.rewrite.pass_a.edit_budget == pytest.approx(0.15)
    assert settings.rewrite.pass_b.edit_budget == pytest.approx(0.35)
    assert settings.rewrite.pass_a.author_review is False


def test_missing_key_raises_config_error(tmp_path: Path) -> None:
    raw = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text(encoding="utf-8"))
    del raw["budget"]  # drop a whole required section
    broken = tmp_path / "config"
    broken.mkdir()
    (broken / "settings.yaml").write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(broken, env_file=None)


def test_settings_immutable() -> None:
    settings = load_settings(CONFIG_DIR, env_file=None)
    with pytest.raises(ValidationError):
        settings.words_per_page = 999  # type: ignore[misc]
    with pytest.raises(ValidationError):
        settings.budget.warn_at = 0.5  # type: ignore[misc]


def test_log_line_json_round_trip(tmp_path: Path) -> None:
    log_path = logging_setup.setup_logging(tmp_path / "logs")
    logging_setup.run_id.set("run-123")
    logging_setup.agent.set("tester")
    try:
        logging_setup.get_logger("core").info("hello core")
    finally:
        logging_setup.run_id.set(None)
        logging_setup.agent.set(None)
    for handler in logging.getLogger("sots").handlers:
        handler.flush()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert lines, "expected at least one log line"
    entry = json.loads(lines[-1])
    assert entry["message"] == "hello core"
    assert entry["run_id"] == "run-123"
    assert entry["agent"] == "tester"
    assert entry["level"] == "INFO"


def test_draft_raises() -> None:
    with pytest.raises(WriterDisabledError):
        draft("chapter one")
    assert issubclass(WriterDisabledError, SotsError)
