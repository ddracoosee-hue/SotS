"""Shared pytest fixtures for the SotS test suite (P00 skeleton)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_settings(tmp_path: Path) -> Path:
    """Placeholder: path to an isolated settings dir for config-loading tests.

    Later phases will write a minimal settings.yaml here and return a loaded
    Settings object; for the P00 skeleton it just provides the directory.
    """
    settings_dir = tmp_path / "settings"
    settings_dir.mkdir()
    return settings_dir
