"""Whole-book notes: dashboard numbers + reading order (OI-42).

The dashboard is computed purely from the foundation snapshot and chapter
states — no LLM, no network — so the book-as-a-whole view is always cheap
to rebuild and never stale past the last `sots vault sync`.
"""

from __future__ import annotations

from typing import Any

from sots.models.run import ChapterState
from sots.models.vault import VaultFoundation, VaultNote
from sots.vault import paths
from sots.vault.paths import chapter_id_from_anchor, chapter_link, wikilink


def _cell(value: Any) -> str:
    """Collapse a value to one table-safe cell (no pipes or newlines)."""
    return " ".join(str(value).split()).replace("|", "/")


def _phase_of(foundation: VaultFoundation, chapter_id: str) -> tuple[str, str]:
    for phase in foundation.phases:
        if chapter_id in (phase.get("chapters") or []):
            return str(phase.get("id", "")), str(phase.get("name", ""))
    return "", ""


def _arc_entry(foundation: VaultFoundation, chapter_id: str) -> dict[str, Any]:
    for entry in foundation.arc:
        if entry.get("ch") == chapter_id:
            return dict(entry)
    return {}


def _anchors_for(foundation: VaultFoundation, chapter_id: str) -> list[dict[str, Any]]:
    return [
        a
        for a in foundation.anchors
        if chapter_id_from_anchor(str(a.get("id", ""))) == chapter_id
    ]


def _motif_count(foundation: VaultFoundation, chapter_id: str) -> int:
    count = 0
    for serial in foundation.motif_serials:
        plan = serial.get("plan") or {}
        if isinstance(plan, dict) and (chapter_id in plan or "all" in plan):
            count += 1
    return count


def _pipeline_cell(state: ChapterState | None) -> str:
    """Compact pipeline status: act, gate tally, blocked flag, or "—"."""
    if state is None:
        return "—"
    gates = state.gate_status or {}
    passed = sum(1 for v in gates.values() if str(v).lower() == "passed")
    cell = f"Act {state.act} · {passed}/{len(gates)} gates"
    if state.blocked_reasons:
        cell += f" · BLOCKED ({len(state.blocked_reasons)})"
    return cell


def build_dashboard_note(foundation: VaultFoundation) -> VaultNote:
    """Whole-book numbers: chapters, protocols, hotspots, message coverage."""
    order = foundation.reading_order or list(foundation.chapter_ids)
    lines = ["# Book Dashboard", ""]
    lines.append("> Whole-book numbers, computed by `sots vault sync`.")
    lines.append("")
    lines.append("## Chapters at a glance")
    lines.append("")
    lines.append("| # | Chapter | Phase | Msgs | Anchors | Protocols | Motifs | Pipeline |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for pos, chapter_id in enumerate(order, start=1):
        phase_id, _ = _phase_of(foundation, chapter_id)
        owned = _anchors_for(foundation, chapter_id)
        protocols = sum(1 for a in owned if a.get("type") == "protocol")
        messages = len(foundation.chapter_messages.get(chapter_id, []))
        lines.append(
            f"| {pos} | {chapter_link(chapter_id)} | {phase_id or '—'} | {messages} "
            f"| {len(owned)} | {protocols} | {_motif_count(foundation, chapter_id)} "
            f"| {_pipeline_cell(foundation.chapter_states.get(chapter_id))} |"
        )
    if not order:
        lines.append("| — | _No chapters yet._ | — | — | — | — | — | — |")
    lines.append("")
    lines.extend(_protocol_inventory_lines(foundation))
    lines.append("")
    lines.extend(_hotspot_lines(foundation))
    lines.append("")
    lines.extend(_coverage_lines(foundation))
    return VaultNote(
        rel_path=paths.BOOK_DASHBOARD_NOTE,
        frontmatter={"tags": ["moc", "book", "dashboard"]},
        generated_body="\n".join(lines) + "\n",
    )


def _protocol_inventory_lines(foundation: VaultFoundation) -> list[str]:
    """Every protocol anchor across the book (the demand-cap input, 23 §7)."""
    protocols = [a for a in foundation.anchors if a.get("type") == "protocol"]
    lines = [f"## Protocol inventory ({len(protocols)} across the book)", ""]
    if not protocols:
        return [*lines, "- _No protocols recorded._"]
    lines.append("| ID | Chapter | Protocol | Evidence grade claimed |")
    lines.append("| --- | --- | --- | --- |")
    for anchor in protocols:
        aid = str(anchor.get("id", ""))
        owner = chapter_id_from_anchor(aid) or "—"
        owner_cell = wikilink(paths.chapter_stem(owner), owner) if owner != "—" else "—"
        lines.append(
            f"| {wikilink(paths.anchor_stem(aid), aid)} | {owner_cell} "
            f"| {_cell(anchor.get('text', ''))} "
            f"| {_cell(anchor.get('tier_claimed', '—') or '—')} |"
        )
    lines.append("")
    lines.append(
        "_Weekly time budgets arrive with the Protocol Load Auditor (P16); "
        "until then this table is the full list to demand-cap._"
    )
    return lines


def _hotspot_lines(foundation: VaultFoundation) -> list[str]:
    """Anchors reused across chapters, hottest first (Repetition Manager input)."""
    reused = [a for a in foundation.anchors if a.get("reuse")]
    reused.sort(key=lambda a: len(a.get("reuse") or []), reverse=True)
    lines = ["## Reuse hotspots", ""]
    if not reused:
        return [*lines, "- _None recorded._"]
    lines.append("| Anchor | Owner | Reused in |")
    lines.append("| --- | --- | --- |")
    for anchor in reused:
        aid = str(anchor.get("id", ""))
        owner = chapter_id_from_anchor(aid) or "—"
        owner_cell = wikilink(paths.chapter_stem(owner), owner) if owner != "—" else "—"
        targets = [str(c) for c in (anchor.get("reuse") or [])]
        links = ", ".join(wikilink(paths.chapter_stem(c), c) for c in targets)
        lines.append(
            f"| {wikilink(paths.anchor_stem(aid), aid)} | {owner_cell} "
            f"| {len(targets)}: {links} |"
        )
    return lines


def _coverage_lines(foundation: VaultFoundation) -> list[str]:
    """Which chapters serve each book-level message."""
    lines = ["## Message coverage", ""]
    if not foundation.book_messages:
        return [*lines, "- _No book messages recorded._"]
    lines.append("| Book message | Served by |")
    lines.append("| --- | --- |")
    for message in foundation.book_messages:
        mid = str(message.get("id", ""))
        served: list[str] = []
        for chapter_id, messages in foundation.chapter_messages.items():
            for child in messages:
                if mid in (child.get("book") or []):
                    cid = str(child.get("id", ""))
                    served.append(
                        f"{wikilink(paths.chapter_stem(chapter_id), chapter_id)} "
                        f"(via {wikilink(paths.message_stem(cid), cid)})"
                    )
        lines.append(
            f"| {wikilink(paths.message_stem(mid), mid)} "
            f"| {len(served)}: {', '.join(served) if served else '—'} |"
        )
    return lines


def build_reading_order_note(foundation: VaultFoundation) -> VaultNote:
    """Architecture note: order, arc, phases, hard dependencies."""
    order = foundation.reading_order or list(foundation.chapter_ids)
    lines = ["# Reading Order", ""]
    lines.append(f"_Status: {foundation.architecture_status}_")
    lines.append("")
    lines.append("| Pos | Chapter | Arc role | Intensity |")
    lines.append("| --- | --- | --- | --- |")
    for pos, chapter_id in enumerate(order, start=1):
        arc = _arc_entry(foundation, chapter_id)
        lines.append(
            f"| {pos} | {chapter_link(chapter_id)} "
            f"| {_cell(arc.get('role', '—'))} | {arc.get('intensity', '—')} |"
        )
    lines.append("")
    lines.append("## Hard dependencies")
    lines.append("")
    if foundation.hard_dependencies:
        lines.extend(f"- {dep}" for dep in foundation.hard_dependencies)
    else:
        lines.append("- _None recorded._")
    return VaultNote(
        rel_path=f"{paths.ARCH_DIR}/Reading Order.md",
        frontmatter={"tags": ["architecture"]},
        generated_body="\n".join(lines) + "\n",
    )
