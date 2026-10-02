"""Architecture lint guard (P01 T01.040).

Fails when SQL (`sqlite3` / `execute(`) appears outside `storage/`, or when
HTTP/model-SDK calls appear outside `providers/` and `agents/tools/`.
"""

from __future__ import annotations

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

SQL_MARKERS = ("sqlite3", "execute(", "executescript(")
HTTP_MARKERS = (
    "httpx",
    "import openai",
    "from openai",
    "import anthropic",
    "from anthropic",
    "AsyncOpenAI",
    "AsyncAnthropic",
    "generativeai",
    "mistralai",
    "import cohere",
    "from cohere",
    "aiohttp",
)


def _iter_py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _is_under(path: Path, root: Path, *parts: str) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return False
    prefix = "sots/" + "/".join(parts)
    return rel == prefix or rel.startswith(prefix + "/")


def find_sql_violations(src_root: Path = SRC_ROOT) -> list[str]:
    """Files using SQL markers outside `sots/storage/`."""
    violations: list[str] = []
    for path in _iter_py_files(src_root):
        if _is_under(path, src_root, "storage"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for marker in SQL_MARKERS:
            if marker in text:
                violations.append(f"{path}: SQL marker {marker!r} outside storage/")
                break
    return violations


def find_http_violations(src_root: Path = SRC_ROOT) -> list[str]:
    """Files using HTTP/SDK markers outside providers/ and agents/tools/."""
    violations: list[str] = []
    for path in _iter_py_files(src_root):
        if _is_under(path, src_root, "providers"):
            continue
        if _is_under(path, src_root, "agents", "tools"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for marker in HTTP_MARKERS:
            if marker in text:
                violations.append(
                    f"{path}: HTTP/SDK marker {marker!r}"
                    " outside providers/ and agents/tools/"
                )
                break
    return violations


def test_no_sql_outside_storage() -> None:
    violations = find_sql_violations()
    assert violations == [], "\n".join(violations)


def test_no_http_or_sdk_calls_outside_allowed_dirs() -> None:
    violations = find_http_violations()
    assert violations == [], "\n".join(violations)


def test_guard_catches_planted_violations(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "sots" / "verify").mkdir(parents=True)
    (src / "sots" / "storage").mkdir(parents=True)
    (src / "sots" / "providers").mkdir(parents=True)
    (src / "sots" / "agents" / "tools").mkdir(parents=True)

    planted_sql = src / "sots" / "verify" / "rogue.py"
    planted_sql.write_text(
        "import sqlite3\nconn.execute('SELECT 1')\n", encoding="utf-8"
    )
    planted_http = src / "sots" / "verify" / "caller.py"
    planted_http.write_text("import httpx\n", encoding="utf-8")
    (src / "sots" / "storage" / "ok.py").write_text(
        "import sqlite3\n", encoding="utf-8"
    )
    (src / "sots" / "providers" / "ok.py").write_text(
        "import httpx\n", encoding="utf-8"
    )
    (src / "sots" / "agents" / "tools" / "ok.py").write_text(
        "import httpx\n", encoding="utf-8"
    )

    sql_hits = find_sql_violations(src)
    assert len(sql_hits) == 1 and "rogue.py" in sql_hits[0]
    http_hits = find_http_violations(src)
    assert len(http_hits) == 1 and "caller.py" in http_hits[0]
