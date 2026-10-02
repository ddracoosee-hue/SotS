"""W0: lane invariant plugins register through the anchor-block module."""

from __future__ import annotations

from pathlib import Path

from sots.agents.failsafes.f20_invariants import (
    InvariantContext,
    check_all,
    registered_invariants,
)


def test_plugin_invariants_registered_from_lane_modules(tmp_path: Path) -> None:
    """The two relocated checks load via invariant_plugins and report."""
    import sots.agents.failsafes.invariant_plugins  # noqa: F401

    names = registered_invariants()
    assert names["raw_files_unchanged"].__module__ == "sots.ingest.invariants"
    assert names["offset_integrity"].__module__ == "sots.segment.invariants"
    report = check_all(InvariantContext(root=tmp_path))
    assert report["raw_files_unchanged"] != []  # no db: violation reported
    assert report["offset_integrity"] != []
