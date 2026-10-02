"""LLM brief parsing: chNN_brief.md to ChapterBrief (P04A T04A.010-T04A.011, 23 §2).

The model extracts structure; this module links anchors to the registry
(exact id, else rapidfuzz at >= 85, else reported unregistered), assigns
dictation/protocol ids, and enforces the Block Contract (T04A.011).
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from rapidfuzz import fuzz, process

from sots.config import Settings
from sots.errors import ValidationFailedError
from sots.foundation.anchors import AnchorRegistry
from sots.models.foundation import Block, ChapterBrief, DictationPrompt, Protocol
from sots.providers.base import LLMProvider
from sots.providers.budget import BudgetNode
from sots.providers.context_pack import ContextPack
from sots.providers.router import RoutingConfig
from sots.providers.structured import call_structured
from sots.storage.db import Connection

#: Fuzzy-match floor for anchor texts (same bar as P09 entity resolution).
FUZZY_THRESHOLD = 85

#: Standalone budget for one parse (brief in, structured brief out).
PARSE_BUDGET_TOKENS = 200_000

_BLOCK_NAMES = (
    "hook_targeting",
    "paradigm_shift",
    "core_mechanism",
    "case_study",
    "actionable_implementation",
    "integration_reflection",
)


class ParsedProtocol(BaseModel):
    """One protocol as the model reports it (ids assigned after)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    steps: str
    evidence_grade_claimed: str | None = None
    evidence_basis_claimed: str | None = None


class ParsedBlock(BaseModel):
    """One block as the model reports it (anchor refs unresolved)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    number: int
    name: str
    structural_purpose: str
    old_belief: str | None = None
    new_belief: str | None = None
    anchor_refs: list[str] = []
    dictation_prompts: list[str] = []
    protocols: list[ParsedProtocol] = []
    journaling_prompts: list[str] = []
    tables: list[dict[str, Any]] = []


class ParseBriefOut(BaseModel):
    """The model's structured reading of one brief (prompt output_model)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    subtitle: str
    phase_claimed: str | None = None
    core_theme: str
    blocks: list[ParsedBlock] = []
    voice_rules: list[str] = []
    appendix_system_prompt: str = ""


class UnregisteredAnchor(BaseModel):
    """An anchor text that matched no registry id (→ proposed addition)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    block: int
    text: str


class ParseReport(BaseModel):
    """What linking found beyond the ChapterBrief itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unregistered_anchors: list[UnregisteredAnchor] = []
    warnings: list[str] = []


def link_anchor(
    ref: str, chapter_id: str, registry: AnchorRegistry
) -> str | None:
    """An anchor ref to a registry id (exact, else fuzzy >= 85, else None)."""
    cleaned = ref.strip()
    if registry.by_id(cleaned) is not None:
        return cleaned
    choices = {anchor.id: anchor.text for anchor in registry.by_chapter(chapter_id)}
    if not choices or not cleaned:
        return None
    best = process.extractOne(cleaned, choices, scorer=fuzz.token_set_ratio)
    if best is not None and best[1] >= FUZZY_THRESHOLD:
        return str(best[2])
    return None


def validate_parsed(chapter_id: str, parsed: ParseBriefOut) -> list[str]:
    """Block Contract violations (T04A.011); empty means valid."""
    violations: list[str] = []
    numbers = [block.number for block in parsed.blocks]
    if numbers != [1, 2, 3, 4, 5, 6]:
        violations.append(f"{chapter_id}: blocks must be exactly 1-6, got {numbers}")
    for block in parsed.blocks:
        if block.name not in _BLOCK_NAMES:
            violations.append(f"{chapter_id}: block {block.number} bad name {block.name!r}")
    by_number = {block.number: block for block in parsed.blocks}
    paradigm = by_number.get(2)
    if paradigm is not None and not (paradigm.old_belief and paradigm.new_belief):
        violations.append(f"{chapter_id}: Block 2 needs old_belief + new_belief")
    action = by_number.get(5)
    if action is not None and len(action.protocols) != 3:
        violations.append(
            f"{chapter_id}: Block 5 needs exactly 3 protocols,"
            f" got {len(action.protocols)}"
        )
    integration = by_number.get(6)
    if integration is not None and len(integration.journaling_prompts) < 3:
        violations.append(
            f"{chapter_id}: Block 6 needs >= 3 journaling prompts,"
            f" got {len(integration.journaling_prompts)}"
        )
    return violations


def _assemble(
    chapter_id: str, parsed: ParseBriefOut, registry: AnchorRegistry
) -> tuple[ChapterBrief, ParseReport]:
    """Link anchors, assign ids, and build the ChapterBrief."""
    unregistered: list[UnregisteredAnchor] = []
    warnings: list[str] = []
    blocks: list[Block] = []
    protocol_seq = 0
    for parsed_block in parsed.blocks:
        anchor_ids: list[str] = []
        for ref in parsed_block.anchor_refs:
            linked = link_anchor(ref, chapter_id, registry)
            if linked is None:
                unregistered.append(UnregisteredAnchor(block=parsed_block.number, text=ref))
            elif linked not in anchor_ids:
                anchor_ids.append(linked)
        prompts = [
            DictationPrompt(id=f"{chapter_id}.B{parsed_block.number}.P{index}", text=text)
            for index, text in enumerate(parsed_block.dictation_prompts, start=1)
        ]
        protocols: list[Protocol] = []
        for parsed_protocol in parsed_block.protocols:
            protocol_seq += 1
            protocols.append(Protocol(
                id=f"{chapter_id}.P{protocol_seq}",
                name=parsed_protocol.name,
                steps=parsed_protocol.steps,
                evidence_grade_claimed=parsed_protocol.evidence_grade_claimed,
                evidence_basis_claimed=parsed_protocol.evidence_basis_claimed,
            ))
        blocks.append(Block.model_validate({
            "number": parsed_block.number,
            "name": parsed_block.name,
            "structural_purpose": parsed_block.structural_purpose,
            "old_belief": parsed_block.old_belief,
            "new_belief": parsed_block.new_belief,
            "anchors": anchor_ids,
            "dictation_prompts": [p.model_dump() for p in prompts],
            "protocols": [p.model_dump() for p in protocols],
            "journaling_prompts": list(parsed_block.journaling_prompts),
            "tables": list(parsed_block.tables),
        }))
    if not parsed.appendix_system_prompt:
        warnings.append(f"{chapter_id}: empty appendix_system_prompt")
    brief = ChapterBrief(
        chapter_id=chapter_id,
        title=parsed.title,
        subtitle=parsed.subtitle,
        phase_claimed=parsed.phase_claimed,
        core_theme=parsed.core_theme,
        blocks=blocks,
        voice_rules_from_appendix=list(parsed.voice_rules),
        appendix_system_prompt=parsed.appendix_system_prompt,
    )
    return brief, ParseReport(unregistered_anchors=unregistered, warnings=warnings)


async def parse_brief(
    chapter_id: str,
    brief_text: str,
    *,
    registry: AnchorRegistry,
    run_id: str,
    conn: Connection,
    settings: Settings,
    routing: RoutingConfig,
    providers: Mapping[str, LLMProvider],
    prompts_dir: str | Path = "prompts",
    brief_path: str = "",
    max_tokens: int = PARSE_BUDGET_TOKENS,
) -> tuple[ChapterBrief, ParseReport]:
    """Parse one brief: LLM extract, link, validate, assemble (T04A.010)."""
    catalog = "\n".join(
        f"{anchor.id} [{anchor.type}]: {anchor.text}"
        for anchor in registry.by_chapter(chapter_id)
    )
    pack = ContextPack(task="foundation.parse_brief", system_role="", pieces=[])
    parsed = await call_structured(
        "foundation.parse_brief", "foundation/parse_brief",
        {"chapter_id": chapter_id, "brief": brief_text, "anchor_catalog": catalog},
        ParseBriefOut, pack, run_id, conn=conn, settings=settings,
        routing=routing, registry=providers,
        budget=BudgetNode(f"parse:{chapter_id}", max_tokens),
        prompts_dir=prompts_dir, prompt_version=1,
    )
    violations = validate_parsed(chapter_id, parsed)
    if violations:
        raise ValidationFailedError("; ".join(violations))
    brief, report = _assemble(chapter_id, parsed, registry)
    brief = brief.model_copy(update={
        "raw_brief_path": brief_path,
        "brief_hash": hashlib.sha256(brief_text.encode("utf-8")).hexdigest(),
    })
    return brief, report
