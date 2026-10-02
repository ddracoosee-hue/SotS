"""Budgeted context packs for LLM calls (P02 T02.020-T02.022, 04 §4).

Every call gets standing context ahead of its task input. Each task declares
its pieces in `TASK_PIECES` (priority order); piece budgets come from
`settings.context.budgets`, scaled by provider window (x min(4, window/32000)).
Over-budget pieces fall back to their summary, then to sentence-safe trimming
— text is never cut mid-sentence and packs never exceed budget.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from sots.config import ContextBudgets
from sots.errors import ConfigError

#: Task -> context pieces in priority order. Covers every routing.yaml task;
#: `rewrite.*` uses the Style Guide, `legal.*` uses issue context, and
#: `audience.persona_read` uses the persona card + journey spec (T02.020).
TASK_PIECES: dict[str, list[str]] = {
    # --- Core pipeline (04 §3-§4) ---
    "summarize.chunk": ["book_profile"],
    "segment.extract_units": ["book_profile", "chapter_brief"],
    "classify.unit": ["book_profile", "chapter_brief", "neighbours"],
    "classify.safety_scan": ["book_profile", "neighbours"],
    "research.plan_queries": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "verify.researcher": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "verify.skeptic": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "verify.adjudicator": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "media.identify": ["neighbours"],
    "media.check": ["book_profile", "chapter_brief", "core_messages", "neighbours", "supplements"],
    "psyche.emotion": ["book_profile", "document_summary", "neighbours"],
    "psyche.cognitive": [
        "book_profile", "chapter_brief", "core_messages", "author_profile", "document_summary",
    ],
    "psyche.theme": [
        "book_profile", "chapter_brief", "core_messages", "author_profile", "document_summary",
    ],
    "psyche.archetype": [
        "book_profile", "chapter_brief", "core_messages", "author_profile", "document_summary",
    ],
    "psyche.blindspot": [
        "book_profile", "chapter_brief", "core_messages", "author_profile", "document_summary",
    ],
    "psyche.reader": [
        "book_profile", "chapter_brief", "core_messages", "document_summary", "neighbours",
    ],
    "psyche.synthesize": [
        "book_profile", "chapter_brief", "core_messages", "document_summary",
    ],
    "narrative.map_messages": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "narrative.voice": ["book_profile", "chapter_brief", "author_profile", "document_summary"],
    "shadow.reflect": [
        "book_profile", "chapter_brief", "core_messages", "author_profile", "document_summary",
    ],
    "shadow.grade": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    # --- Fact-check specialists + scouts (06 §9) ---
    "fact_check.triage": ["book_profile", "neighbours"],
    "fact_check.stats": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "fact_check.courts": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "fact_check.academic": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "fact_check.social": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "fact_check.quotes": ["book_profile", "chapter_brief", "neighbours", "supplements"],
    "fact_check.discovery_scout": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "fact_check.media_scout": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    # --- Expansion team (11 §6) ---
    "expand.concepts": ["book_profile", "core_messages", "neighbours"],
    "expand.merge": ["book_profile", "core_messages", "neighbours"],
    "expand.link": [
        "book_profile", "chapter_brief", "core_messages", "document_summary", "neighbours",
    ],
    "expand.propose": [
        "book_profile", "chapter_brief", "core_messages", "document_summary", "neighbours",
    ],
    "expand.brief": [
        "book_profile", "chapter_brief", "core_messages", "document_summary", "neighbours",
    ],
    "expand.queries": ["book_profile", "neighbours", "supplements"],
    "expand.read": ["book_profile", "chapter_brief", "core_messages", "supplements"],
    "expand.report": ["book_profile", "chapter_brief", "core_messages", "supplements"],
    "expand.dialogue": ["book_profile", "chapter_brief", "document_summary", "neighbours"],
    "expand.chat": ["book_profile", "chapter_brief", "document_summary", "neighbours"],
    "expand.integrate": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "expand.critic": ["book_profile", "core_messages", "neighbours"],
    # --- Rewrite teams (19 §7): Style Guide is a piece ---
    "rewrite.mechanic_adjudicate": ["book_profile", "style_guide", "neighbours"],
    "rewrite.format_structure": ["book_profile", "style_guide", "neighbours"],
    "rewrite.line_edit": [
        "book_profile", "chapter_brief", "core_messages", "author_profile",
        "style_guide", "neighbours",
    ],
    "rewrite.master": [
        "book_profile", "chapter_brief", "core_messages", "author_profile",
        "style_guide", "neighbours",
    ],
    "rewrite.weave": [
        "book_profile", "chapter_brief", "core_messages", "author_profile",
        "style_guide", "neighbours",
    ],
    "rewrite.style_guide": ["book_profile", "author_profile", "style_guide", "neighbours"],
    "rewrite.style_report": ["book_profile", "style_guide", "neighbours"],
    "rewrite.cross_check": [
        "book_profile", "chapter_brief", "style_guide", "neighbours", "supplements",
    ],
    "rewrite.entailment": ["book_profile", "style_guide", "neighbours"],
    # --- Audience lab + learning (20 §8) ---
    "audience.mechanics_explain": ["book_profile", "chapter_brief", "neighbours"],
    "audience.persona_read": [
        "book_profile", "chapter_brief", "persona_card", "journey_spec", "neighbours",
    ],
    "audience.takeaway_match": ["chapter_brief", "core_messages", "neighbours"],
    "audience.brief": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "learning.summarize": ["book_profile", "core_messages"],
    # --- Legal chamber (22 §8): issue context is a piece ---
    "legal.screen": ["book_profile", "chapter_brief", "issue_context", "neighbours"],
    "legal.counsel": [
        "book_profile", "chapter_brief", "issue_context", "neighbours", "supplements",
    ],
    "legal.synthesize": ["book_profile", "issue_context", "neighbours"],
    "legal.entailment": ["issue_context", "neighbours"],
    # --- Quality gate judges (17 §4) ---
    "grader.judge_a": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "grader.judge_b": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    "grader.judge_c": ["book_profile", "chapter_brief", "core_messages", "neighbours"],
    # --- Proposal desk (18 §4) ---
    "proposals.draft": [
        "book_profile", "chapter_brief", "core_messages", "neighbours", "supplements",
    ],
    "proposals.chat": [
        "book_profile", "chapter_brief", "core_messages", "neighbours", "supplements",
    ],
    # --- Foundation (23 §3) ---
    "foundation.parse_brief": ["book_profile", "chapter_brief", "neighbours"],
    "classify.block_map": [
        "book_profile", "chapter_brief", "f3_block", "neighbours",
    ],
}

#: Tasks whose output is pipeline metadata, not book content (no F1/F2).
NON_CONTENT_TASKS = frozenset({"learning.summarize"})

# R-FOUND-01: every content task loads at least F1 + F2 (23 §3, 01 §D4).
for _task, _pieces in TASK_PIECES.items():
    if _task not in NON_CONTENT_TASKS:
        rest = [_p for _p in _pieces if _p not in ("f1_book", "f2_chapter")]
        _pieces[:] = ["f1_book", "f2_chapter", *rest]
del _task, _pieces

PIECE_TITLES: dict[str, str] = {
    "book_profile": "Book profile",
    "chapter_brief": "Chapter brief",
    "core_messages": "Core messages",
    "author_profile": "Author profile",
    "document_summary": "Document summary",
    "neighbours": "Neighbouring units",
    "supplements": "Supplement excerpts",
    "style_guide": "Style guide",
    "issue_context": "Legal issue context",
    "persona_card": "Persona card",
    "journey_spec": "Reader journey spec",
    "f1_book": "F1 Book Card",
    "f2_chapter": "F2 Chapter Card",
    "f3_block": "F3 Block Card",
    "f4_anchors": "F4 Anchor Card",
    "f5_voice": "F5 Voice Card",
    "f6_arc": "F6 Arc Card",
}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class PieceInput(BaseModel):
    """Full text plus its summarized fallback for one piece."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = ""
    summary: str = ""


class ContextSources(BaseModel):
    """Standing context available to pack builders (stages fill what they have)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    system_role: str = ""
    book_profile: PieceInput = PieceInput()
    chapter_brief: PieceInput = PieceInput()
    core_messages: PieceInput = PieceInput()
    author_profile: PieceInput = PieceInput()
    document_summary: PieceInput = PieceInput()
    neighbours: PieceInput = PieceInput()
    supplements: PieceInput = PieceInput()
    style_guide: PieceInput = PieceInput()
    issue_context: PieceInput = PieceInput()
    persona_card: PieceInput = PieceInput()
    journey_spec: PieceInput = PieceInput()
    f1_book: PieceInput = PieceInput()
    f2_chapter: PieceInput = PieceInput()
    f3_block: PieceInput = PieceInput()
    f4_anchors: PieceInput = PieceInput()
    f5_voice: PieceInput = PieceInput()
    f6_arc: PieceInput = PieceInput()


class ContextPiece(BaseModel):
    """One budgeted piece in a built pack."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    text: str
    budget: int
    truncated: bool = False


class ContextPack(BaseModel):
    """Built pack: system role + budgeted pieces, ready to render."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    task: str
    system_role: str
    pieces: list[ContextPiece]


def scale_factor(context_window: int) -> float:
    """Budget multiplier for a provider window: min(4, window/32000) (04 §4)."""
    if context_window <= 0:
        raise ValueError("context_window must be positive")
    return min(4.0, context_window / 32000)


def trim_to_budget(text: str, max_tokens: int, counter: Callable[[str], int]) -> str:
    """Trim to whole leading sentences that fit; "" when none fit (04 §4).

    Never cuts mid-sentence: the result is always a prefix of complete
    sentences (whitespace-normalized between them).
    """
    if not text.strip() or max_tokens <= 0:
        return ""
    if counter(text) <= max_tokens:
        return text
    sentences = [s for s in _SENTENCE_SPLIT.split(text.strip()) if s]
    kept: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*kept, sentence])
        if counter(candidate) <= max_tokens:
            kept.append(sentence)
        else:
            break
    return " ".join(kept)


def build(
    task: str,
    sources: ContextSources,
    *,
    budgets: ContextBudgets,
    context_window: int,
    counter: Callable[[str], int],
) -> ContextPack:
    """Assemble a task's pack: full text, else summary, else trimmed (04 §4)."""
    piece_names = TASK_PIECES.get(task)
    if piece_names is None:
        raise ConfigError(f"no context pieces registered for task {task!r}")
    scale = scale_factor(context_window)
    budget_map = budgets.model_dump()
    pieces: list[ContextPiece] = []
    for name in piece_names:
        budget = int(budget_map[name] * scale)
        piece_input: PieceInput = getattr(sources, name)
        text, truncated = _fit_piece(piece_input, budget, counter)
        pieces.append(ContextPiece(name=name, text=text, budget=budget, truncated=truncated))
    return ContextPack(task=task, system_role=sources.system_role, pieces=pieces)


def _fit_piece(
    piece: PieceInput, budget: int, counter: Callable[[str], int]
) -> tuple[str, bool]:
    if not piece.text.strip():
        return "", False
    if counter(piece.text) <= budget:
        return piece.text, False
    if piece.summary.strip() and counter(piece.summary) <= budget:
        return piece.summary, True
    fallback = piece.summary if piece.summary.strip() else piece.text
    return trim_to_budget(fallback, budget, counter), True


def render(pack: ContextPack) -> str:
    """Pack to system-message text; empty pieces are skipped."""
    sections = [pack.system_role] if pack.system_role.strip() else []
    for piece in pack.pieces:
        if not piece.text.strip():
            continue
        title = PIECE_TITLES.get(piece.name, piece.name)
        sections.append(f"## {title}\n{piece.text}")
    return "\n\n".join(sections)


def pack_tokens(pack: ContextPack, counter: Callable[[str], int]) -> int:
    """Token count of the rendered pack (budget verification)."""
    return counter(render(pack))
