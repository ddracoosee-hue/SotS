"""Generate the P05 segment fixtures (T05.011): short/medium/long docs.

Varied book-like paragraphs with an embedded index so no two sentences repeat.
Run from the repo root: `uv run python tests/fixtures/docs/generate.py`.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATES = [
    "The phone buzzed for the {n}th time that morning, and Maya felt her "
    "attention scatter like marbles across a tile floor. She had promised "
    "herself one hour of deep work before noon, yet the pull of the feed "
    "proved stronger than her intention. Researchers call this habit loop "
    "variable reward conditioning, and it shapes millions of mornings.",
    "Nobody explained to Daniel that boredom was a doorway rather than a "
    "defect, so he filled every pause of day {n} with noise. On the train, "
    "in the elevator, even walking the dog, his ears carried voices that "
    "were never his own. The silence he feared might have told him who he "
    "was becoming, if only he had let it speak.",
    "Craft teaches what lectures cannot: the wood resists, the chisel slips, "
    "and lesson {n} arrives through the hands before the mind. Elena spent "
    "three evenings shaping a single dovetail joint, failing twice before "
    "the pieces slid together with a soft click. That click, she says, "
    "reorganized her understanding of patience more than any book.",
    "The statistics arrive every quarter and nobody reads past the headline, "
    "yet finding {n} deserves a slower look. When comparison runs all day, "
    "contentment leaks out through a thousand small comparisons. The cure "
    "is not ignorance of the numbers but a sturdier story about what the "
    "numbers are allowed to mean for a single human life.",
    "Grace perplexed Thomas because every other economy of day {n} ran on "
    "exchange and score. Somebody kept giving without invoice, forgiving "
    "without negotiation, and it broke his spreadsheet of deservedness. He "
    "began to suspect that the deepest realities operate by gift rather "
    "than by transaction, and the suspicion changed his posture.",
    "Laughter erupted at table {n} over nothing consequential, and the "
    "whole evening tilted toward warmth. Nobody remembers the joke now, "
    "only the Duchenne crinkle around tired eyes and the loosening of "
    "shoulders that had carried the week. Joy, it turns out, is a team "
    "sport disguised as a spontaneous accident.",
    "Shame kept Ruth rehearsing conversations from week {n} long after "
    "everyone else had forgotten them. She replayed her stumble at the "
    "microphone, the pause, the nervous laugh, each replay etching the "
    "groove deeper. What finally freed her was not a better performance "
    "but one witness who stayed kind through the retelling.",
    "The third place on corner {n} serves coffee and something harder to "
    "name: membership without a card. Regulars argue about sports, share "
    "grief in low voices, and borrow tools across fences built by zoning "
    "laws. Nobody optimized this belonging; it grew like moss in the "
    "cracks of an over-scheduled neighborhood.",
    "Attention is the substance of a life, wrote the philosopher, and "
    "paragraph {n} keeps testing whether that claim survives contact with "
    "a smartphone. Every glance is a small vote for what the mind will "
    "become skilled at noticing. The skill compounds quietly, toward "
    "either presence or fragmentation, and the interest never sleeps.",
    "The manuscript draft for chapter {n} sat untouched while its author "
    "rearranged his desk for the fifth time. Resistance, he learned, "
    "wears the costume of preparation and speaks in the voice of reason. "
    "He wrote one true sentence, then another, and the desk stayed messy "
    "but the page finally began to fill.",
]

TARGETS = {"short": 1_000, "medium": 8_000, "long": 52_000}


def build(words: int) -> str:
    """Cycle templates until past `words` words (paragraph-separated)."""
    paras: list[str] = []
    total = 0
    n = 1
    while total < words:
        para = TEMPLATES[(n - 1) % len(TEMPLATES)].format(n=n)
        paras.append(para)
        total += len(para.split())
        n += 1
    return "\n\n".join(paras) + "\n"


def main() -> None:
    out = Path(__file__).resolve().parent
    for name, target in TARGETS.items():
        text = build(target)
        (out / f"{name}.md").write_text(text, encoding="utf-8", newline="\n")
        print(f"{name}.md: {len(text.split())} words")


if __name__ == "__main__":
    main()
