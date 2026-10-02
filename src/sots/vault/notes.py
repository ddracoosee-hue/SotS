"""Managed-note builders: foundation snapshot -> wikilinked notes (OI-42)."""

from __future__ import annotations

from typing import Any

from sots.models.vault import VaultFoundation, VaultNote
from sots.vault import paths
from sots.vault.paths import chapter_id_from_anchor, chapter_link, wikilink


def _phase_of(foundation: VaultFoundation, chapter_id: str) -> tuple[str, str, str]:
    """(phase id, phase name, movement) for a chapter, or blanks."""
    for phase in foundation.phases:
        if chapter_id in (phase.get("chapters") or []):
            return (
                str(phase.get("id", "")),
                str(phase.get("name", "")),
                str(phase.get("movement", "")),
            )
    return "", "", ""


def _arc_entry(foundation: VaultFoundation, chapter_id: str) -> dict[str, Any]:
    for entry in foundation.arc:
        if entry.get("ch") == chapter_id:
            return dict(entry)
    return {}


def _anchors_for_chapter(
    foundation: VaultFoundation, chapter_id: str
) -> list[dict[str, Any]]:
    return [
        a
        for a in foundation.anchors
        if chapter_id_from_anchor(str(a.get("id", ""))) == chapter_id
    ]


def _motifs_for_chapter(
    foundation: VaultFoundation, chapter_id: str
) -> list[tuple[str, str]]:
    """(motif, role) pairs whose serial plan touches this chapter."""
    hits: list[tuple[str, str]] = []
    for serial in foundation.motif_serials:
        motif = str(serial.get("motif", ""))
        plan = serial.get("plan") or {}
        if not isinstance(plan, dict):
            continue
        if chapter_id in plan:
            hits.append((motif, str(plan[chapter_id])))
        elif "all" in plan:
            hits.append((motif, str(plan["all"])))
    return hits


def _pipeline_lines(foundation: VaultFoundation, chapter_id: str) -> list[str]:
    """Act/gate/blocked lines from SQLite chapter state, or a not-run note."""
    state = foundation.chapter_states.get(chapter_id)
    if state is None:
        return ["_The pipeline has not run for this chapter yet._"]
    lines = [f"- Act: {state.act}"]
    if state.gate_status:
        gates = ", ".join(f"{gate}={status}" for gate, status in state.gate_status.items())
        lines.append(f"- Gates: {gates}")
    else:
        lines.append("- Gates: _none recorded_")
    if state.blocked_reasons:
        lines.extend(f"- Blocked: {reason}" for reason in state.blocked_reasons)
    return lines


def build_book_index(foundation: VaultFoundation) -> VaultNote:
    """Map of content: reading order, phases, motifs, messages."""
    order = foundation.reading_order or list(foundation.chapter_ids)
    lines = ["# The Subject of the Self — Book Index", ""]
    lines.append("> Map of content. Rebuilt by `sots vault sync` from `profile/`.")
    lines.append("")
    lines.append("## Reading order")
    lines.append("")
    for pos, chapter_id in enumerate(order, start=1):
        phase_id, phase_name, _ = _phase_of(foundation, chapter_id)
        phase = f" — {phase_id} {phase_name}".rstrip() if phase_id else ""
        lines.append(f"{pos}. {chapter_link(chapter_id)}{phase}")
    lines.append("")
    lines.append("## Phases")
    lines.append("")
    for phase in foundation.phases:
        chapters = ", ".join(
            wikilink(paths.chapter_stem(c), c) for c in (phase.get("chapters") or [])
        )
        lines.append(
            f"- **{phase.get('id', '?')} · {phase.get('name', '?')}**: {chapters}"
        )
        if phase.get("movement"):
            lines.append(f"  - _{phase['movement']}_")
    if not foundation.phases:
        lines.append("- _No phases recorded yet._")
    lines.append("")
    lines.append("## Whole-book threads")
    lines.append("")
    motifs = [wikilink(paths.motif_stem(m), m) for m in _motif_names(foundation)]
    lines.append(f"- Motifs: {', '.join(motifs) if motifs else '_none_'}")
    book_ids = [str(m.get("id", "")) for m in foundation.book_messages]
    book_links = ", ".join(wikilink(paths.message_stem(i), i) for i in book_ids)
    lines.append(f"- Book messages: {book_links if book_links else '_none_'}")
    lines.append(f"- {wikilink('Book Dashboard')}: chapter counts, protocols, hotspots")
    lines.append(f"- {wikilink('Author Notes Digest')}: your margin notes, in one place")
    lines.append("")
    lines.append("## Chapters")
    lines.append("")
    for chapter_id in foundation.chapter_ids:
        lines.append(f"- {chapter_link(chapter_id)}")
    return VaultNote(
        rel_path=paths.BOOK_INDEX_NOTE,
        frontmatter={"tags": ["moc", "book"], "aliases": ["Index"]},
        generated_body="\n".join(lines) + "\n",
    )


def _motif_names(foundation: VaultFoundation) -> list[str]:
    return [str(s.get("motif", "")) for s in foundation.motif_serials if s.get("motif")]


def build_chapter_note(foundation: VaultFoundation, chapter_id: str) -> VaultNote:
    """One chapter: position, arc, messages, anchors, reuse, motifs."""
    title = paths.chapter_title(chapter_id)
    order = foundation.reading_order or list(foundation.chapter_ids)
    pos = order.index(chapter_id) + 1 if chapter_id in order else 0
    phase_id, phase_name, _ = _phase_of(foundation, chapter_id)
    prev_link = wikilink(paths.chapter_stem(order[pos - 2]), order[pos - 2]) if pos > 1 else "—"
    next_link = (
        wikilink(paths.chapter_stem(order[pos]), order[pos]) if pos < len(order) else "—"
    )
    lines = [f"# {chapter_id} — {title}", ""]
    lines.append("## Reading position")
    lines.append("")
    lines.append(
        f"Position {pos} of {len(order)} · Phase {phase_id} ({phase_name})"
        if phase_id
        else f"Position {pos} of {len(order)}"
    )
    lines.append(f"Prev: {prev_link} · Next: {next_link}")
    lines.append("")
    arc = _arc_entry(foundation, chapter_id)
    if arc:
        lines.append("## Arc role")
        lines.append("")
        lines.append(f"{arc.get('role', '')} _(intensity {arc.get('intensity', '?')}/10)_")
        lines.append("")
    lines.append("## Messages")
    lines.append("")
    messages = foundation.chapter_messages.get(chapter_id, [])
    if messages:
        for message in messages:
            mid = str(message.get("id", ""))
            book = message.get("book") or []
            book_links = ", ".join(wikilink(paths.message_stem(b), b) for b in book)
            book_suffix = f" → {book_links}" if book_links else ""
            lines.append(
                f"- {wikilink(paths.message_stem(mid), mid)} "
                f"(P{message.get('priority', '?')}): {message.get('statement', '')}"
                f"{book_suffix}"
            )
    else:
        lines.append("- _No chapter messages recorded._")
    lines.append("")
    lines.append("## Anchors in this chapter")
    lines.append("")
    anchors = _anchors_for_chapter(foundation, chapter_id)
    if anchors:
        for anchor in anchors:
            aid = str(anchor.get("id", ""))
            lines.append(
                f"- {wikilink(paths.anchor_stem(aid), aid)} "
                f"[{anchor.get('type', '?')} · B{anchor.get('block', '?')}]: "
                f"{anchor.get('text', '')}"
            )
    else:
        lines.append("- _No anchors recorded._")
    lines.append("")
    lines.append("## Cross-chapter reuse")
    lines.append("")
    lines.extend(_reuse_lines(foundation, chapter_id))
    lines.append("")
    lines.append("## Motif threads")
    lines.append("")
    motifs = _motifs_for_chapter(foundation, chapter_id)
    if motifs:
        for motif, role in motifs:
            lines.append(f"- {wikilink(paths.motif_stem(motif), motif)}: {role}")
    else:
        lines.append("- _No motif serials touch this chapter._")
    lines.append("")
    lines.append("## Brief")
    lines.append("")
    lines.append(f"Source: `profile/chapters/{chapter_id}_brief.md`")
    header = foundation.brief_headers.get(chapter_id, "")
    if header:
        lines.append(f"> {header}")
    lines.append("")
    lines.append("## Pipeline state")
    lines.append("")
    lines.extend(_pipeline_lines(foundation, chapter_id))
    frontmatter: dict[str, Any] = {
        "chapter_id": chapter_id,
        "title": title,
        "phase": phase_id or None,
        "reading_position": pos or None,
        "tags": ["chapter"],
        "aliases": [chapter_id],
    }
    return VaultNote(
        rel_path=paths.chapter_note_rel_path(chapter_id),
        frontmatter=frontmatter,
        generated_body="\n".join(lines) + "\n",
    )


def _reuse_lines(foundation: VaultFoundation, chapter_id: str) -> list[str]:
    """Cross-chapter anchor traffic for one chapter, both directions."""
    outward: list[str] = []
    for anchor in _anchors_for_chapter(foundation, chapter_id):
        aid = str(anchor.get("id", ""))
        reuse = [c for c in (anchor.get("reuse") or []) if c != chapter_id]
        if reuse:
            targets = ", ".join(wikilink(paths.chapter_stem(c), c) for c in reuse)
            outward.append(f"- {wikilink(paths.anchor_stem(aid), aid)} → {targets}")
    inward: list[str] = []
    for anchor in foundation.anchors:
        aid = str(anchor.get("id", ""))
        owner = chapter_id_from_anchor(aid)
        if owner is None or owner == chapter_id:
            continue
        if chapter_id in (anchor.get("reuse") or []):
            inward.append(
                f"- {wikilink(paths.anchor_stem(aid), aid)} "
                f"(from {chapter_link(owner)})"
            )
    lines = ["**From here, reused elsewhere:**"]
    lines.extend(outward or ["- _None recorded._"])
    lines.append("**From elsewhere, used here:**")
    lines.extend(inward or ["- _None recorded._"])
    return lines


def build_anchor_note(anchor: dict[str, Any]) -> VaultNote:
    """One anchor: claim, ownership, reuse backlinks, flags."""
    aid = str(anchor.get("id", ""))
    owner = chapter_id_from_anchor(aid) or ""
    reuse = anchor.get("reuse") or []
    lines = [f"# {aid}", ""]
    lines.append(f"> {anchor.get('text', '')}")
    lines.append("")
    owner_link = chapter_link(owner) if owner else "—"
    lines.append(f"- Chapter: {owner_link} · Block {anchor.get('block', '?')}")
    lines.append(
        f"- Type: `{anchor.get('type', '?')}` · Claim: "
        f"`{anchor.get('claim_kind', '—')}`"
    )
    lines.append(
        f"- Tier claimed: {anchor.get('tier_claimed', '—')} · "
        f"Status: {anchor.get('status', 'active')}"
    )
    if anchor.get("serial"):
        lines.append(f"- Serial: `{anchor['serial']}`")
    if anchor.get("provenance"):
        lines.append(f"- Provenance: `{anchor['provenance']}`")
    if anchor.get("author_decision"):
        lines.append(f"- Author decision: {anchor['author_decision']}")
    targets = ", ".join(wikilink(paths.chapter_stem(c), c) for c in reuse)
    lines.append(f"- Reused in: {targets if targets else '—'}")
    lines.append("")
    lines.append("## Preflags (unverified leads)")
    lines.append("")
    preflags = anchor.get("preflags") or []
    if preflags:
        lines.extend(f"- {flag}" for flag in preflags)
    else:
        lines.append("- _None._")
    lines.append("")
    lines.append("## Legal notes")
    lines.append("")
    legal = anchor.get("legal") or []
    if legal:
        lines.extend(f"- {note}" for note in legal)
    else:
        lines.append("- _None._")
    frontmatter: dict[str, Any] = {
        "anchor_id": aid,
        "chapter": owner or None,
        "block": anchor.get("block"),
        "type": anchor.get("type"),
        "claim_kind": anchor.get("claim_kind"),
        "tier_claimed": anchor.get("tier_claimed"),
        "status": anchor.get("status", "active"),
        "tags": ["anchor"],
    }
    return VaultNote(
        rel_path=paths.anchor_note_rel_path(aid),
        frontmatter=frontmatter,
        generated_body="\n".join(lines) + "\n",
    )


def build_message_note(
    message_id: str,
    statement: str,
    priority: Any,
    level: str,
    chapter_id: str | None,
    foundation: VaultFoundation,
) -> VaultNote:
    """One message: statement plus the chapters/threads it binds together."""
    lines = [f"# {message_id}", ""]
    lines.append(f"> {statement}")
    lines.append("")
    lines.append(f"- Level: {level} · Priority: {priority}")
    if chapter_id:
        lines.append(f"- Chapter: {chapter_link(chapter_id)}")
    if level == "book":
        served: list[str] = []
        for ch, messages in foundation.chapter_messages.items():
            for message in messages:
                if message_id in (message.get("book") or []):
                    cid = str(message.get("id", ""))
                    served.append(
                        f"{wikilink(paths.chapter_stem(ch), ch)} "
                        f"(via {wikilink(paths.message_stem(cid), cid)})"
                    )
        lines.append(f"- Served by: {', '.join(served) if served else '—'}")
    else:
        book_ids = _book_ids_for(foundation, chapter_id or "", message_id)
        book_links = ", ".join(wikilink(paths.message_stem(b), b) for b in book_ids)
        lines.append(f"- Serves: {book_links if book_links else '—'}")
    frontmatter: dict[str, Any] = {
        "message_id": message_id,
        "level": level,
        "chapter": chapter_id,
        "priority": priority,
        "tags": ["message"],
    }
    return VaultNote(
        rel_path=paths.message_note_rel_path(message_id),
        frontmatter=frontmatter,
        generated_body="\n".join(lines) + "\n",
    )


def _book_ids_for(
    foundation: VaultFoundation, chapter_id: str, message_id: str
) -> list[str]:
    for message in foundation.chapter_messages.get(chapter_id, []):
        if str(message.get("id", "")) == message_id:
            return [str(b) for b in (message.get("book") or [])]
    return []


def build_motif_note(motif: str, plan: dict[str, Any]) -> VaultNote:
    """One motif serial: the per-chapter teaching/callback plan."""
    lines = [f"# Motif: {motif}", ""]
    lines.append("| Chapter | Role in this chapter |")
    lines.append("| --- | --- |")
    for chapter_id, role in plan.items():
        if chapter_id == "all":
            lines.append(f"| _all_ | {role} |")
        elif paths.is_chapter_id(chapter_id):
            lines.append(f"| {chapter_link(chapter_id)} | {role} |")
        else:
            lines.append(f"| {chapter_id} | {role} |")
    return VaultNote(
        rel_path=paths.motif_note_rel_path(motif),
        frontmatter={"motif": motif, "tags": ["motif"]},
        generated_body="\n".join(lines) + "\n",
    )
