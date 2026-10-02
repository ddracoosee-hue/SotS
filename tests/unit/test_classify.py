"""P06 safety/classify/consistency tests (T06.001-T06.004)."""

from __future__ import annotations

import json
from pathlib import Path

from sots.agents.events import EventBus
from sots.classify.classifier import classify_unit
from sots.classify.consistency import ClassificationOut, validate_consistency
from sots.classify.safety_scan import run_safety_scan
from sots.config import load_settings
from sots.models.enums import Checkability, ContentType
from sots.models.unit import Unit
from sots.providers.context_pack import ContextSources, PieceInput
from sots.providers.fake import FakeProvider
from sots.providers.prompts import load_prompt
from sots.providers.router import RoutingConfig, RoutingTask
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
PROMPTS_DIR = ROOT / "prompts"

TABLE_ROWS = [
    "It describes what happened to the author/their family/friends",
    'It states an opinion, value, or "I believe/feel"',
    "It tells the reader what to do or what to learn",
    "It contains a number, percentage, or rate about the world",
    "It names a lawsuit, trial, ruling, or legal outcome",
    'It describes a viral post, influencer, online controversy, or "a TikTok where…"',
    "It cites research, science, or psychology findings",
    "It names or retells a book, film, show, song, game, or podcast",
    'It says "X said…"',
    "Metaphor, transition, or a hook with no claim",
]


def test_classify_prompt_verbatim() -> None:
    """T06.002: the decision table verbatim + 7 worked examples."""
    prompt = load_prompt(PROMPTS_DIR, "classify/classify_unit", 1)
    assert prompt.output_model == "ClassificationOut"
    assert set(prompt.variables) == {"unit_id", "unit_text", "retry_notes"}
    for row in TABLE_ROWS:
        assert row in prompt.body, row
    for content in (
        "personal_experience", "personal_belief", "lesson_advice",
        "factual_claim", "media_reference", "question_reflection",
        "narrative_device",
    ):
        assert f'"content_type": "{content}"' in prompt.body, content


def test_safety_prompt() -> None:
    prompt = load_prompt(PROMPTS_DIR, "classify/safety_scan", 1)
    assert prompt.output_model == "SafetyScanOut"
    assert set(prompt.variables) == {"units"}
    assert "R-PSY-04" in prompt.body


def _unit(uid: str, text: str) -> Unit:
    return Unit(
        id=uid, document_id="d", chunk_id="c", run_id="r", order=0,
        text=text, start_char=0, end_char=len(text),
    )


def _routing(*tasks: str) -> RoutingConfig:
    return RoutingConfig(
        fallback_order=[],
        tasks={name: RoutingTask(
            provider="fake", temperature=0.0, max_output_tokens=1000
        ) for name in tasks},
    )


async def test_safety_scan_flags_and_continues(tmp_path: Path) -> None:
    """T06.001: crisis text flags, emits, and never blocks."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        units = [
            _unit("u-calm", "The sky was blue that morning."),
            _unit("u-crisis", "I want to kill myself tonight."),
        ]
        for unit in units:
            storage_repo.save_unit(conn, unit)
        fake = FakeProvider()
        fake.script_default("classify.safety_scan", [
            {"text": json.dumps({"flags": [
                {"unit_id": "u-crisis", "reason": "present-tense self-harm intent"},
                {"unit_id": "u-ghost", "reason": "hallucinated id"},
            ]})},
        ])
        bus = EventBus()
        queue = bus.subscribe("author.input_needed")
        flagged = await run_safety_scan(
            units, run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None),
            routing=_routing("classify.safety_scan"), providers={"fake": fake},
            prompts_dir=PROMPTS_DIR, bus=bus,
        )
        assert flagged == ["u-crisis"]  # pipeline continued past the flag
        assert storage_repo.get_unit(conn, "u-crisis").safety_flag is True
        assert storage_repo.get_unit(conn, "u-calm").safety_flag is False
        event = queue.get_nowait()
        assert event.payload["type"] == "safety_notice"
        assert event.payload["unit_id"] == "u-crisis"
        assert queue.empty()
    finally:
        conn.close()


def _out(**fields: object) -> ClassificationOut:
    base: dict[str, object] = {
        "content_type": ContentType.PERSONAL_BELIEF,
        "checkability": Checkability.NOT_CHECKABLE,
    }
    base.update(fields)
    return ClassificationOut.model_validate(base)


def test_rule_claim_kind_iff_factual() -> None:
    """T06.004 rule 1 (pass + fail)."""
    assert validate_consistency(_out(
        content_type=ContentType.FACTUAL_CLAIM, claim_kind="statistic",
        checkability=Checkability.CHECKABLE, normalized_claim="N",
    )) == []
    assert len(validate_consistency(_out(claim_kind="statistic"))) == 1
    assert len(validate_consistency(_out(
        content_type=ContentType.FACTUAL_CLAIM,
        checkability=Checkability.CHECKABLE, normalized_claim="N",
    ))) == 1


def test_rule_media_kind_iff_media() -> None:
    """T06.004 rule 2 (pass + fail)."""
    assert validate_consistency(_out(
        content_type=ContentType.MEDIA_REFERENCE, media_kind="film",
        checkability=Checkability.CHECKABLE, normalized_claim="N",
    )) == []
    assert len(validate_consistency(_out(media_kind="film"))) == 1
    assert len(validate_consistency(_out(
        content_type=ContentType.MEDIA_REFERENCE,
        checkability=Checkability.CHECKABLE, normalized_claim="N",
    ))) == 1


def test_rule_not_checkable_bare() -> None:
    """T06.004 rule 3 (pass + fail)."""
    assert validate_consistency(_out()) == []
    assert len(validate_consistency(_out(normalized_claim="N"))) == 1
    assert len(validate_consistency(_out(embedded_claims=["E"]))) == 1


def test_rule_media_never_not_checkable() -> None:
    """T06.004 rule 4 (pass + fail)."""
    assert validate_consistency(_out(
        content_type=ContentType.MEDIA_REFERENCE, media_kind="film",
        checkability=Checkability.PARTIAL,
    )) == []
    assert len(validate_consistency(_out(
        content_type=ContentType.MEDIA_REFERENCE, media_kind="film",
    ))) == 1


async def test_classify_unit_fake(tmp_path: Path) -> None:
    """T06.003: one unit through the FakeProvider with neighbour context."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        fake.script_default("classify.unit", [
            {"text": json.dumps({
                "content_type": "factual_claim", "claim_kind": "statistic",
                "media_kind": None, "checkability": "checkable",
                "entities": ["CDC"], "normalized_claim": "N",
                "embedded_claims": [], "confidence": 0.9,
            })},
        ])
        out = await classify_unit(
            "u1", "Rates hit 50%.", run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None),
            routing=_routing("classify.unit"), providers={"fake": fake},
            prompts_dir=PROMPTS_DIR,
            sources=ContextSources(
                neighbours=PieceInput(text="NEIGHBOUR MARKER")),
        )
        assert out is not None and out.claim_kind == "statistic"
        assert out.confidence == 0.9
        assert "NEIGHBOUR MARKER" in fake.calls[0].system
    finally:
        conn.close()


async def test_classify_retry_then_failed(tmp_path: Path) -> None:
    """Inconsistent output retries once with the errors, then gives up."""
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    try:
        fake = FakeProvider()
        bad = {"content_type": "personal_belief", "claim_kind": "statistic",
               "checkability": "not_checkable", "confidence": 0.5}
        good = {"content_type": "factual_claim", "claim_kind": "statistic",
                "checkability": "checkable", "normalized_claim": "N",
                "confidence": 0.9}
        fake.script_default("classify.unit", [
            {"text": json.dumps(bad)}, {"text": json.dumps(good)},
        ])
        kwargs = dict(
            run_id="r1", conn=conn,
            settings=load_settings(CONFIG_DIR, env_file=None),
            routing=_routing("classify.unit"), providers={"fake": fake},
            prompts_dir=PROMPTS_DIR,
        )
        out = await classify_unit("u1", "Rates hit 50%.", **kwargs)
        assert out is not None and out.content_type == ContentType.FACTUAL_CLAIM
        assert len(fake.calls) == 2
        assert "claim_kind must be set" in fake.calls[1].messages[0]["content"]
        # A stubborn model fails instead of guessing.
        fake.script_default("classify.unit", [{"text": json.dumps(bad)}])
        assert await classify_unit("u9", "Other text.", **kwargs) is None
    finally:
        conn.close()
