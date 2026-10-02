"""P04A brief-parser tests (T04A.010-T04A.011, 23 §2)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sots.config import load_settings
from sots.errors import ValidationFailedError
from sots.foundation.anchors import AnchorRegistry
from sots.foundation.brief_parser import (
    ParseBriefOut,
    link_anchor,
    parse_brief,
    validate_parsed,
)
from sots.foundation.loader import load_foundation
from sots.providers.fake import FakeProvider
from sots.providers.router import RoutingConfig, RoutingTask
from sots.storage import db as storage_db

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"
PROFILE_DIR = ROOT / "profile"
FIXTURES = ROOT / "tests" / "fixtures" / "briefs"


@pytest.fixture
def conn(tmp_path: Path):
    handle = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(handle)
    yield handle
    handle.close()


def _routing() -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={
            "foundation.parse_brief": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=8000
            )
        },
    )


def _registry() -> AnchorRegistry:
    return AnchorRegistry(load_foundation(PROFILE_DIR).anchors)


async def _parse_fixture(chapter_id: str, conn) -> tuple:
    text = (FIXTURES / f"{chapter_id}.json").read_text(encoding="utf-8")
    fake = FakeProvider()
    fake.script_default("foundation.parse_brief", [{"text": text}])
    brief_text = (PROFILE_DIR / "chapters" / f"{chapter_id}_brief.md").read_text(
        encoding="utf-8"
    )
    return await parse_brief(
        chapter_id, brief_text, registry=_registry(), run_id="r1", conn=conn,
        settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
        providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        brief_path=f"profile/chapters/{chapter_id}_brief.md",
    )


def test_fixtures_are_valid_outputs() -> None:
    """The canned LLM outputs parse as ParseBriefOut and pass validation."""
    for chapter_id in ("ch01", "ch05", "ch11"):
        parsed = ParseBriefOut.model_validate_json(
            (FIXTURES / f"{chapter_id}.json").read_text(encoding="utf-8")
        )
        assert validate_parsed(chapter_id, parsed) == []


async def test_parse_ch01(conn) -> None:
    """T04A.010: exact + fuzzy anchor links, one unregistered, ids assigned."""
    brief, report = await _parse_fixture("ch01", conn)
    assert brief.chapter_id == "ch01"
    assert [block.number for block in brief.blocks] == [1, 2, 3, 4, 5, 6]
    assert brief.blocks[0].anchors == ["ch01.A05"]
    assert brief.blocks[1].anchors == ["ch01.A05"]
    assert len(report.unregistered_anchors) == 1
    assert "llamas" in report.unregistered_anchors[0].text
    assert report.unregistered_anchors[0].block == 3
    assert brief.blocks[0].dictation_prompts[0].id == "ch01.B1.P1"
    assert [p.id for p in brief.blocks[4].protocols] == ["ch01.P1", "ch01.P2", "ch01.P3"]
    assert brief.voice_rules_from_appendix != []
    assert "APPENDIX-SENTINEL-ch01" in brief.appendix_system_prompt
    assert brief.brief_hash == hashlib.sha256(
        (PROFILE_DIR / "chapters" / "ch01_brief.md").read_text(encoding="utf-8").encode()
    ).hexdigest()


async def test_parse_ch05_and_ch11(conn) -> None:
    """T04A.010: the other two layouts parse to the same contract."""
    brief5, report5 = await _parse_fixture("ch05", conn)
    assert brief5.blocks[0].anchors == ["ch05.A04"]
    assert brief5.blocks[1].anchors == ["ch05.A04"]
    assert len(report5.unregistered_anchors) == 1
    assert brief5.blocks[4].protocols[2].id == "ch05.P3"

    brief11, report11 = await _parse_fixture("ch11", conn)
    assert brief11.blocks[0].anchors == ["ch11.A08"]
    assert len(report11.unregistered_anchors) == 1
    assert [b.name for b in brief11.blocks[:2]] == ["hook_targeting", "paradigm_shift"]


def test_link_anchor_paths() -> None:
    registry = _registry()
    assert link_anchor("ch01.A05", "ch01", registry) == "ch01.A05"
    assert link_anchor("  ch01.A05  ", "ch01", registry) == "ch01.A05"
    assert link_anchor("ch01.A05", "ch05", registry) == "ch01.A05"  # ids are global
    assert link_anchor("nope, nothing like this xyzzy", "ch01", registry) is None
    assert link_anchor("", "ch01", registry) is None


def _parsed(**overrides) -> ParseBriefOut:
    base = json.loads((FIXTURES / "ch01.json").read_text(encoding="utf-8"))
    base.update(overrides)
    return ParseBriefOut.model_validate(base)


def test_validation_contract() -> None:
    """T04A.011: the Block Contract rejects short blocks, B2, B5, B6."""
    assert validate_parsed("ch01", _parsed()) == []
    short = _parsed(blocks=_parsed().blocks[:5])
    assert any("exactly 1-6" in v for v in validate_parsed("ch01", short))
    no_beliefs = json.loads((FIXTURES / "ch01.json").read_text(encoding="utf-8"))
    no_beliefs["blocks"][1]["old_belief"] = None
    no_beliefs["blocks"][1]["new_belief"] = ""
    assert any(
        "Block 2" in v
        for v in validate_parsed("ch01", ParseBriefOut.model_validate(no_beliefs))
    )
    two_protocols = json.loads((FIXTURES / "ch01.json").read_text(encoding="utf-8"))
    two_protocols["blocks"][4]["protocols"] = two_protocols["blocks"][4]["protocols"][:2]
    assert any(
        "exactly 3 protocols" in v
        for v in validate_parsed("ch01", ParseBriefOut.model_validate(two_protocols))
    )
    one_prompt = json.loads((FIXTURES / "ch01.json").read_text(encoding="utf-8"))
    one_prompt["blocks"][5]["journaling_prompts"] = ["only one"]
    assert any(
        "journaling" in v
        for v in validate_parsed("ch01", ParseBriefOut.model_validate(one_prompt))
    )


async def test_parse_rejects_bad_output(conn) -> None:
    fake = FakeProvider()
    bad = json.loads((FIXTURES / "ch01.json").read_text(encoding="utf-8"))
    bad["blocks"] = bad["blocks"][:5]
    fake.script_default("foundation.parse_brief", [{"text": json.dumps(bad)}])
    with pytest.raises(ValidationFailedError, match="exactly 1-6"):
        await parse_brief(
            "ch01", "brief", registry=_registry(), run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None), routing=_routing(),
            providers={"fake": fake}, prompts_dir=PROMPTS_DIR,
        )
