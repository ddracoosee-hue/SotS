"""P00 C1: the six skeleton config files parse and rubrics weights sum to 1.0."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

CONFIG_FILES = [
    "settings.yaml",
    "routing.yaml",
    "source_tiers.yaml",
    "rubrics.yaml",
    "system_goals.yaml",
    "safety.yaml",
]


def _no_dup_loader():
    """A SafeLoader that raises on duplicate mapping keys."""

    class NoDupLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=True)
            if key in mapping:
                raise ValueError(f"duplicate key: {key!r}")
            mapping[key] = loader.construct_object(value_node, deep=True)
        return mapping

    NoDupLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    return NoDupLoader


@pytest.mark.parametrize("filename", CONFIG_FILES)
def test_config_file_parses(filename: str) -> None:
    path = CONFIG_DIR / filename
    assert path.is_file(), f"missing {path}"
    with path.open(encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=_no_dup_loader())
    assert isinstance(data, dict), f"{filename} must parse to a mapping"


def test_rubrics_weights_sum_to_one() -> None:
    with (CONFIG_DIR / "rubrics.yaml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    weights = [c["weight"] for c in data["criteria"]]
    assert len(weights) == 9
    assert sum(weights) == pytest.approx(1.0)


def test_routing_task_keys_unique() -> None:
    with (CONFIG_DIR / "routing.yaml").open(encoding="utf-8") as fh:
        text = fh.read()
    data = yaml.load(text, Loader=_no_dup_loader())
    assert "tasks" in data and len(data["tasks"]) > 0


def test_safety_has_both_keys() -> None:
    with (CONFIG_DIR / "safety.yaml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert "crisis_resources" in data
    assert "banned_labels" in data
    assert len(data["banned_labels"]) > 0


# --- P00 C2 (T00.026-T00.031) ---

C2_CONFIG_FILES = [
    "teams.yaml",
    "grader.yaml",
    "formatting.yaml",
    "personas.yaml",
    "legal.yaml",
    "audience/thresholds.yaml",
    "audience/targets.yaml",
    "audience/techniques.yaml",
]


@pytest.mark.parametrize("filename", C2_CONFIG_FILES)
def test_c2_config_file_parses(filename: str) -> None:
    path = CONFIG_DIR / filename
    assert path.is_file(), f"missing {path}"
    with path.open(encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=_no_dup_loader())
    assert isinstance(data, dict), f"{filename} must parse to a mapping"


def test_grader_rubric_weights_sum_to_one() -> None:
    """Every rubric in grader.yaml (17 S3.1-3.5, 22 S5) sums to 1.0."""
    with (CONFIG_DIR / "grader.yaml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    rubrics = data["rubrics"]
    assert set(rubrics) == {
        "proposal",
        "rewrite_hunk",
        "research_report",
        "legal_memo",
        "audience_brief",
        "legal_argument",
    }
    for rubric_id, rubric in rubrics.items():
        weights = [c["weight"] for c in rubric["criteria"]]
        assert sum(weights) == pytest.approx(1.0), f"{rubric_id} weights sum to {sum(weights)}"


def test_personas_all_adults() -> None:
    """Template set: 12 adult personas (20 §4.1), all age ≥ 18."""
    with (CONFIG_DIR / "personas.yaml").open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert data["constraints"]["min_age"] == 18
    assert data["reviewed"] is False
    personas = data["personas"]
    assert len(personas) == 12
    cohorts = [p["cohort"] for p in personas]
    assert cohorts.count("gen_z_adult") == 7
    assert cohorts.count("millennial") == 4
    assert cohorts.count("gen_x") == 1
    for persona in personas:
        assert persona["age"] >= 18, f"{persona['id']} age {persona['age']}"


WORD_LISTS = [
    "cliches.txt",
    "dated_slang.txt",
    "therapy_speak.txt",
    "caricature_markers.txt",
]


@pytest.mark.parametrize("filename", WORD_LISTS)
def test_audience_word_list_has_entries(filename: str) -> None:
    """Each starter word list (20 §3, §4.2) has ≥ 30 entries (T00.030)."""
    path = CONFIG_DIR / "audience" / filename
    assert path.is_file(), f"missing {path}"
    entries = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(entries) >= 30, f"{filename} has only {len(entries)} entries"
