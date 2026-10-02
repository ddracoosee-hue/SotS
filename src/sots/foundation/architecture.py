"""Reading-order queries (P04A T04A.004, 23 §4)."""

from __future__ import annotations

from sots.models.foundation import (
    ArchPhase,
    ArcStep,
    BookArchitecture,
    BriefEdit,
    MotifSerial,
)


class Architecture:
    """Queryable book architecture (positions, phases, arc, motif plans)."""

    def __init__(self, architecture: BookArchitecture) -> None:
        self._arch = architecture
        self._positions = {ch: pos for pos, ch in enumerate(architecture.reading_order)}
        self._phases = {
            chapter: phase
            for phase in architecture.phases
            for chapter in phase.chapters
        }
        self._arc = {step.ch: step for step in architecture.arc}
        self._motifs = {serial.motif: serial for serial in architecture.motif_serials}

    @property
    def reading_order(self) -> list[str]:
        """The reading-order chapter list."""
        return list(self._arch.reading_order)

    @property
    def motif_serials(self) -> list[MotifSerial]:
        """The motif serial plans."""
        return list(self._arch.motif_serials)

    @property
    def brief_edits(self) -> list[BriefEdit]:
        """The required brief edits."""
        return list(self._arch.brief_edits_required)

    @property
    def phases(self) -> list[ArchPhase]:
        """The book phases in order."""
        return list(self._arch.phases)

    def position(self, chapter_id: str) -> int:
        """0-based reading-order position (unknown chapters raise)."""
        try:
            return self._positions[chapter_id]
        except KeyError as exc:
            raise ValueError(f"unknown chapter {chapter_id!r}") from exc

    def phase(self, chapter_id: str) -> ArchPhase | None:
        """The phase containing this chapter, if any."""
        return self._phases.get(chapter_id)

    def arc_step(self, chapter_id: str) -> ArcStep | None:
        """The arc role of this chapter, if any."""
        return self._arc.get(chapter_id)

    def arc_position(self, chapter_id: str) -> int | None:
        """The 1-based arc position of this chapter, if it has an arc step."""
        step = self._arc.get(chapter_id)
        return step.pos if step is not None else None

    def callback_label(self, chapter_id: str) -> str:
        """'Chapter N' in reading order (unknown chapters raise)."""
        return f"Chapter {self.position(chapter_id) + 1}"

    def is_callback(self, motif: str, chapter_id: str) -> bool | None:
        """Whether the plan calls for a callback (None when unplanned).

        A plan entry counts as a callback when it says "callback" without
        "in full"; mixed entries ("a callback ... in full in the tables")
        count as full treatments.
        """
        serial = self._motifs.get(motif)
        if serial is None:
            return None
        entry = serial.plan.get(chapter_id)
        if entry is None:
            return None
        lowered = entry.lower()
        return "callback" in lowered and "in full" not in lowered

    def motif_plan(self, motif: str) -> dict[str, str]:
        """The teach/call-back plan for a motif ({} when unknown)."""
        serial = self._motifs.get(motif)
        return dict(serial.plan) if serial is not None else {}
