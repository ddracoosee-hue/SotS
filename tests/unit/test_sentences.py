"""P05 sentence-splitter tests (T05.001, 04 §5): 20 tricky cases."""

from __future__ import annotations

from sots.segment.sentences import split_sentences


def _texts(text: str) -> list[str]:
    """Split, verifying every span slices its sentence."""
    spans = split_sentences(text)
    return [text[s:e] for s, e in spans]


def test_tricky_twenty() -> None:
    """T05.001: abbreviations, quotes, decimals, initials, ellipsis."""
    assert _texts("Meet Mr. Smith today. He is kind.") == [
        "Meet Mr. Smith today.", "He is kind.",
    ]
    assert _texts("See Dr. Jones now. She waits.") == [
        "See Dr. Jones now.", "She waits.",
    ]
    assert _texts("Bring fruit, e.g. apples and pears.") == [
        "Bring fruit, e.g. apples and pears.",
    ]
    assert _texts("The soul, i.e. the witness, stays.") == [
        "The soul, i.e. the witness, stays.",
    ]
    assert _texts("He works for the U.S. Government daily.") == [
        "He works for the U.S. Government daily.",
    ]
    assert _texts("I like apples, etc. They are crisp.") == [
        "I like apples, etc.", "They are crisp.",
    ]
    assert _texts("Pi is about 3.14. It goes on.") == [
        "Pi is about 3.14.", "It goes on.",
    ]
    assert _texts("J. Cole retired the villain arc. Fans cheered.") == [
        "J. Cole retired the villain arc.", "Fans cheered.",
    ]
    assert _texts('He said "Go home." Then he left.') == [
        'He said "Go home."', "Then he left.",
    ]
    assert _texts("Really?! That is wild. Truly wild!") == [
        "Really?!", "That is wild.", "Truly wild!",
    ]
    assert _texts("Wait... what did you say? Nothing.") == [
        "Wait... what did you say?", "Nothing.",
    ]
    assert _texts("Ask Mrs. Doyle. She knows everything.") == [
        "Ask Mrs. Doyle.", "She knows everything.",
    ]
    # Documented default: U.S. never splits, even at a real boundary.
    assert _texts("He visited the U.S. It was vast.") == ["He visited the U.S. It was vast."]
    assert _texts("One.   Two.\nThree.") == ["One.", "Two.", "Three."]
    assert _texts("First line\nstill the same sentence. Done.") == [
        "First line\nstill the same sentence.", "Done.",
    ]
    assert _texts("") == []
    assert _texts("see Fig. 3 for proof. It holds.") == [
        "see Fig. 3 for proof.", "It holds.",
    ]
    assert _texts('"Go," she said. Then silence.') == [
        '"Go," she said.', "Then silence.",
    ]
    assert _texts("You and I. We left together.") == ["You and I.", "We left together."]
    assert _texts("He left. 3 people followed.") == ["He left.", "3 people followed."]


def test_spans_are_exact() -> None:
    """Spans slice exactly; leading whitespace stays outside."""
    text = "  Hi there. Bye."
    assert split_sentences(text) == [(2, 11), (12, 16)]
