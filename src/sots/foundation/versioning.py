"""Foundation versioning (P04A T04A.005, 23 §6).

Pure helpers: file versions (the `version:` field + sha256), change records
for version bumps, and per-run version snapshots. No database: callers pass
the previous snapshot in and persist what they need.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from sots.models.foundation import FoundationChange

#: Versioned single files, relative to profile/.
TRACKED_FILES = (
    "author.md",
    "book.md",
    "messages.yaml",
    "style_guide_seed.yaml",
    "anchors.yaml",
    "book_architecture.yaml",
    "voice_corpus/manifest.yaml",
)

#: Versioned globs, relative to profile/.
TRACKED_GLOBS = ("chapters/*.md", "chapters/*.yaml", "manuscript/*")


class FileVersion(BaseModel):
    """One tracked file's version field + content hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file: str
    version: int | None
    sha256: str


class FoundationSnapshot(BaseModel):
    """The versions a run executed against (file -> version + short hash)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    versions: dict[str, str]


def file_version(path: str | Path, *, root: str | Path | None = None) -> FileVersion:
    """Version + sha256 of one file (missing files hash empty)."""
    target = Path(path)
    label = str(target.relative_to(root)) if root is not None else target.name
    if not target.is_file():
        return FileVersion(file=label, version=None, sha256="")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    version: int | None = None
    if target.suffix in (".yaml", ".yml"):
        try:
            data = yaml.safe_load(target.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("version"), int):
            version = data["version"]
    return FileVersion(file=label, version=version, sha256=digest)


def foundation_versions(profile_dir: str | Path) -> dict[str, FileVersion]:
    """Versions of every tracked foundation file (existing files only)."""
    root = Path(profile_dir)
    versions: dict[str, FileVersion] = {}
    candidates: list[Path] = [root / name for name in TRACKED_FILES]
    for pattern in TRACKED_GLOBS:
        candidates.extend(sorted(root.glob(pattern)))
    for path in candidates:
        if path.is_file():
            entry = file_version(path, root=root)
            versions[entry.file] = entry
    return versions


def record_change(
    file: str,
    *,
    old: FileVersion | None,
    new: FileVersion | None,
    who: str,
    why: str,
    diff: str = "",
) -> FoundationChange:
    """One version-bump record (23 §6: who, what, why, diff)."""
    if old is None:
        what = "added"
    elif new is None:
        what = "removed"
    elif old.version != new.version:
        what = f"version {old.version} -> {new.version}"
    else:
        what = "content changed (same version)"
    version = (new.version if new is not None else None) or 0
    if new is None and old is not None and old.version is not None:
        version = old.version
    return FoundationChange(
        file=file, version=version, who=who, what=what, why=why, diff=diff,
        created_at=datetime.now(UTC),
    )


def detect_changes(
    old: dict[str, FileVersion], new: dict[str, FileVersion], *, who: str, why: str
) -> list[FoundationChange]:
    """Change records for every added/removed/modified tracked file."""
    changes: list[FoundationChange] = []
    for file in sorted(set(old) | set(new)):
        before, after = old.get(file), new.get(file)
        if before is not None and after is not None and before.sha256 == after.sha256:
            continue
        changes.append(record_change(file, old=before, new=after, who=who, why=why))
    return changes


def run_snapshot(run_id: str, versions: dict[str, FileVersion]) -> FoundationSnapshot:
    """Freeze versions for a run (`?:` marks files without a version field)."""
    return FoundationSnapshot(
        run_id=run_id,
        versions={
            file: f"{entry.version if entry.version is not None else '?'}:"
            f"{entry.sha256[:8]}"
            for file, entry in sorted(versions.items())
        },
    )
