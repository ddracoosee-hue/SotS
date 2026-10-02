"""JSON-lines logging (P00 T00.042).

Run output goes to ``data/logs/sots.jsonl``, one JSON object per line.
The ``run_id`` and ``agent`` context variables let concurrent runs and
agents tag their own lines without passing loggers around.
"""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

run_id: ContextVar[str | None] = ContextVar("sots_run_id", default=None)
"""Current run id attached to every log line; ``None`` when unbound."""

agent: ContextVar[str | None] = ContextVar("sots_agent", default=None)
"""Current agent name attached to every log line; ``None`` when unbound."""


class JsonLinesFormatter(logging.Formatter):
    """Format a record as a single JSON object line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": run_id.get(),
            "agent": agent.get(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(logs_dir: Path | str = "data/logs") -> Path:
    """Attach a JSON-lines handler to the ``sots`` logger.

    Creates ``logs_dir`` and returns the path of ``sots.jsonl``. Calling it
    again with the same directory does not duplicate handlers.
    """
    log_path = Path(logs_dir) / "sots.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sots")
    logger.setLevel(logging.DEBUG)
    for handler in logger.handlers:
        if getattr(handler, "_sots_log_path", None) == str(log_path):
            return log_path
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(JsonLinesFormatter())
    handler._sots_log_path = str(log_path)  # type: ignore[attr-defined]
    logger.addHandler(handler)
    return log_path


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of ``sots`` (``sots.<name>``)."""
    return logging.getLogger(f"sots.{name}")
