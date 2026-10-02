"""F15 size guard: byte/char/row caps with explicit notes (P03 T03.054, 16 §5.1).

Everything trimmed by a cap carries an explicit truncation note — never
silently. Each helper returns (kept, note), where note is None when intact.
"""

from __future__ import annotations


def cap_text(text: str, max_chars: int, label: str) -> tuple[str, str | None]:
    """Cap characters; the note states how much was cut."""
    if len(text) <= max_chars:
        return text, None
    note = f"[{label}: showing {max_chars} of {len(text)} chars]"
    return text[:max_chars] + "\n\n" + note, note


def cap_bytes(data: bytes, max_bytes: int, label: str) -> tuple[bytes, str | None]:
    """Cap bytes (same contract as cap_text)."""
    if len(data) <= max_bytes:
        return data, None
    note = f"[{label}: showing {max_bytes} of {len(data)} bytes]"
    return data[:max_bytes], note


def cap_rows[T](rows: list[T], max_rows: int, label: str) -> tuple[list[T], str | None]:
    """Cap rows (same contract as cap_text)."""
    if len(rows) <= max_rows:
        return rows, None
    note = f"[{label}: showing {max_rows} of {len(rows)} rows]"
    return rows[:max_rows], note
