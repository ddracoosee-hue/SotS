"""SQLite connection + migrations (P01 T01.031).

`connect()` opens the DB with WAL, foreign keys, and Row rows. `migrate()`
applies every pending `migrations/NNN_*.sql` file in order and records it in
`schema_version`, so migrating an empty DB reaches current and re-migrating
is a no-op.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent
SCHEMA_SQL = STORAGE_DIR / "schema.sql"
MIGRATIONS_DIR = STORAGE_DIR / "migrations"

#: Connection type for annotations outside `storage/` (the arch guard forbids
#: the `sqlite3` marker text anywhere else, so import this alias instead).
Connection = sqlite3.Connection


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL, foreign keys, and Row factory."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migration_files() -> list[Path]:
    """Ordered migration SQL files (NNN_name.sql)."""
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(MIGRATIONS_DIR.glob("[0-9]*.sql"))


def current_version(conn: sqlite3.Connection) -> int:
    """Highest applied schema version (0 when nothing applied yet)."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version"
        " (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return int(row["v"]) if row["v"] is not None else 0


def applied_versions(conn: sqlite3.Connection) -> list[int]:
    current_version(conn)  # ensure the table exists
    rows = conn.execute("SELECT version FROM schema_version ORDER BY version").fetchall()
    return [int(r["version"]) for r in rows]


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations in order; return versions applied (may be empty)."""
    files = migration_files()
    if not files:
        raise FileNotFoundError(f"no migration files in {MIGRATIONS_DIR}")
    done = set(applied_versions(conn))
    applied: list[int] = []
    for path in files:
        version = int(path.name.split("_", 1)[0])
        if version in done:
            continue
        with conn:
            conn.executescript(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, _utcnow()),
            )
        applied.append(version)
    return applied


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply schema.sql directly (fresh test DBs; skips version bookkeeping)."""
    with conn:
        conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))


def integrity_check(path: str | Path) -> str:
    """Run `PRAGMA integrity_check` on a DB file; returns its verdict.

    The doctor (F17) probes through this helper so SQL stays inside
    `storage/` (the architecture guard forbids it anywhere else).
    """
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else "empty"
