"""Context Cards F1-F6 (P04A T04A.020, 23 §3).

Each builder returns card text within its 23 §3 token budget (sections drop
from lowest priority until it fits; a sentence-safe trim is the last resort).
Cards never contain brief appendix text (R-FOUND-04); the builders take only
the fields they need, never a whole brief file.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sots.foundation.anchors import AnchorRegistry, normalize
from sots.foundation.architecture import Architecture
from sots.models.foundation import Block, BookArchitecture, BriefAnchor, ChapterBrief
from sots.models.narrative import CoreMessage
from sots.profile.loader import parse_sections
from sots.providers.context_pack import trim_to_budget

#: 23 §3 default budgets (tokens).
CARD_BUDGETS = {
    "f1_book": 400,
    "f2_chapter": 700,
    "f3_block": 600,
    "f4_anchors": 800,
    "f5_voice": 500,
    "f6_arc": 300,
}

Counter = Callable[[str], int]


def _fit_sections(sections: list[str], budget: int, counter: Counter) -> str:
    """Highest-priority sections that fit (sentence-safe trim last)."""
    kept: list[str] = []
    for section in sections:
        if not section.strip():
            continue
        candidate = "\n\n".join([*kept, section])
        if counter(candidate) <= budget or not kept:
            kept.append(section)
    text = "\n\n".join(kept)
    if counter(text) > budget:
        text = trim_to_budget(text, budget, counter)
    return text


def _words_up_to(text: str, limit: int) -> str:
    """First `limit` words, with a cut note when trimmed."""
    words = text.split()
    if len(words) <= limit:
        return text.strip()
    return " ".join(words[:limit]) + " …[cut to budget]"


def f1_book_card(
    book_text: str, architecture: BookArchitecture, counter: Counter
) -> str:
    """F1: premise (≤250w), central question, promise, phases, tone (23 §3)."""
    sections = parse_sections(book_text)
    premise = _words_up_to(sections.get("Premise", ""), 250)
    phases = "; ".join(
        f"{phase.id} {phase.name} ({', '.join(phase.chapters)})"
        for phase in architecture.phases
    )
    parts = [
        "[F1 Book Card]",
        premise,
        sections.get("Central Question", "").strip(),
        sections.get("Promise to the Reader", "").strip(),
        f"Phases: {phases}" if phases else "",
        sections.get("Tone Goals", "").strip(),
    ]
    return _fit_sections(parts, CARD_BUDGETS["f1_book"], counter)


def f2_chapter_card(
    brief: ChapterBrief | None, messages: list[CoreMessage], counter: Counter
) -> str:
    """F2: theme, B2 flip, block purposes, chapter messages (23 §3)."""
    parts = ["[F2 Chapter Card]"]
    if brief is None:
        parts.append("Brief not parsed yet (run: sots foundation parse).")
    else:
        parts.append(brief.core_theme)
        paradigm = next((b for b in brief.blocks if b.number == 2), None)
        if paradigm is not None:
            parts.append(f"Old: {paradigm.old_belief} → New: {paradigm.new_belief}")
        purposes = "; ".join(
            f"B{block.number} {block.name}: {block.structural_purpose}"
            for block in brief.blocks
        )
        parts.append(purposes)
    chapter_msgs = [m for m in messages if m.level == "chapter"]
    book_msgs = [m for m in messages if m.level == "book"]
    parts.append("; ".join(f"{m.id}: {m.statement}" for m in chapter_msgs))
    parts.append("; ".join(f"{m.id}: {m.statement}" for m in book_msgs))
    return _fit_sections(parts, CARD_BUDGETS["f2_chapter"], counter)


def f3_block_card(
    brief: ChapterBrief | None,
    block_number: int,
    registry: AnchorRegistry,
    counter: Counter,
) -> str:
    """F3: one block's purpose, anchors, prompts, protocols (23 §3)."""
    parts = [f"[F3 Block Card B{block_number}]"]
    block: Block | None = None
    if brief is not None:
        block = next((b for b in brief.blocks if b.number == block_number), None)
    if block is None:
        parts.append("Block not parsed yet (run: sots foundation parse).")
        return _fit_sections(parts, CARD_BUDGETS["f3_block"], counter)
    parts.append(f"{block.name}: {block.structural_purpose}")
    for anchor_id in block.anchors:
        anchor = registry.by_id(anchor_id)
        if anchor is None:
            parts.append(f"{anchor_id}: (not in registry)")
        else:
            parts.append(_anchor_slice(anchor))
    parts.append("; ".join(p.text for p in block.dictation_prompts))
    parts.append("; ".join(f"{p.name}: {p.steps}" for p in block.protocols))
    return _fit_sections(parts, CARD_BUDGETS["f3_block"], counter)


def _anchor_slice(anchor: BriefAnchor) -> str:
    """One anchor's card text: id, type, text, preflags."""
    slice_text = f"{anchor.id} [{anchor.type}]: {anchor.text}"
    if anchor.preflags:
        slice_text += " | Watch: " + "; ".join(anchor.preflags)
    return slice_text


def f4_anchor_card(
    registry: AnchorRegistry, scope_texts: list[str], counter: Counter
) -> str:
    """F4: slices for anchors mentioned in scope (entity match, 23 §3)."""
    parts = ["[F4 Anchor Card]"]
    seen: list[str] = []
    for text in scope_texts:
        for anchor_id in registry.match_in_text(text):
            if anchor_id not in seen:
                seen.append(anchor_id)
    for anchor_id in seen:
        anchor = registry.by_id(anchor_id)
        if anchor is not None:
            parts.append(_anchor_slice(anchor))
    if not seen:
        parts.append("No registry anchors matched in scope.")
    return _fit_sections(parts, CARD_BUDGETS["f4_anchors"], counter)


def f5_voice_card(
    seed: Mapping[str, Any], counter: Counter, *, scope_text: str = ""
) -> str:
    """F5: seed do/don't summary + protected terms in scope (23 §3)."""
    parts = ["[F5 Voice Card]"]
    summary = seed.get("voice_summary", "")
    if isinstance(summary, str) and summary.strip():
        parts.append(summary.strip())
    # Terms outrank do/don't prose: exact strings to preserve (23 §3).
    terms = seed.get("protected_terms", [])
    if isinstance(terms, list) and terms:
        texts = [str(t) for t in terms]
        if scope_text.strip():
            scope = normalize(scope_text)
            in_scope = [t for t in texts if normalize(t) in scope]
            texts = in_scope or texts
        parts.append("Protected terms: " + "; ".join(texts))
    dos = seed.get("dos", [])
    donts = seed.get("donts", [])
    if isinstance(dos, list) and dos:
        parts.append("Do: " + "; ".join(str(d) for d in dos))
    if isinstance(donts, list) and donts:
        parts.append("Don't: " + "; ".join(str(d) for d in donts))
    return _fit_sections(parts, CARD_BUDGETS["f5_voice"], counter)


def f6_arc_card(
    architecture: Architecture, chapter_id: str, counter: Counter
) -> str:
    """F6: reading position, neighbors, motif serial steps (23 §3)."""
    parts = ["[F6 Arc Card]"]
    try:
        position = architecture.position(chapter_id)
    except ValueError:
        parts.append(f"Unknown chapter {chapter_id}.")
        return _fit_sections(parts, CARD_BUDGETS["f6_arc"], counter)
    order = architecture.reading_order
    parts.append(f"Reading position {position + 1} of {len(order)}.")
    before = order[position - 1] if position > 0 else "—"
    after = order[position + 1] if position + 1 < len(order) else "—"
    parts.append(f"Before: {before}. After: {after}.")
    phase = architecture.phase(chapter_id)
    if phase is not None:
        parts.append(f"Phase {phase.id} {phase.name}: {phase.movement}")
    step = architecture.arc_step(chapter_id)
    if step is not None:
        parts.append(f"Arc: {step.role}")
    for serial in architecture.motif_serials:
        entry = serial.plan.get(chapter_id)
        if entry:
            parts.append(f"Motif {serial.motif}: {entry}")
    return _fit_sections(parts, CARD_BUDGETS["f6_arc"], counter)
