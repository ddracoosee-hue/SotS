"""F16 kill switch: `data/STOP` + signal handlers (P03 T03.055, 16 §5.1).

`sots stop` (or SIGINT/SIGTERM) creates the STOP file; agents check it
between steps, then finish the current step, checkpoint, and exit.
"""

from __future__ import annotations

import signal
from pathlib import Path
from types import FrameType
from typing import Any

STOP_FILENAME = "STOP"


def stop_path(data_dir: str | Path) -> Path:
    """The kill-switch file for a data dir."""
    return Path(data_dir) / STOP_FILENAME


def is_stopped(data_dir: str | Path) -> bool:
    """True when the operator has engaged the kill switch."""
    return stop_path(data_dir).is_file()


def engage(data_dir: str | Path) -> Path:
    """Engage the kill switch (idempotent); returns the file path."""
    path = stop_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    return path


def clear(data_dir: str | Path) -> bool:
    """Disengage; True when a STOP file was removed."""
    path = stop_path(data_dir)
    if not path.is_file():
        return False
    path.unlink()
    return True


def install_signal_handler(data_dir: str | Path) -> None:
    """SIGINT/SIGTERM engage the switch (handlers chain to the default)."""

    def _handle(signum: int, frame: FrameType | None) -> Any:
        _ = (signum, frame)
        engage(data_dir)

    signal.signal(signal.SIGINT, _handle)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle)
