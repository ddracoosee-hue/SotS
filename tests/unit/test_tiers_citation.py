"""P07 tiers/citation/passages tests (T07.030-T07.032)."""

from __future__ import annotations

from pathlib import Path

from sots.research.passages import trim_passages
from sots.research.tiers import classify_url, load_tier_rules
from sots.verify.citation_check import verify_excerpt

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def test_tier_urls() -> None:
    """T07.030: 16 URLs against the real source_tiers.yaml."""
    rules = load_tier_rules(CONFIG_DIR / "source_tiers.yaml")
    cases = [
        ("https://courtlistener.com/opinion/1", (1, "primary_record")),
        ("https://www.courtlistener.com/x", (1, "primary_record")),
        ("https://census.gov/data", (1, "primary_record")),
        ("https://data.census.gov/table", (1, "primary_record")),
        ("https://doi.org/10.1000/xyz", (2, "academic")),
        # *.gov precedes the pubmed rule: nih.gov is tier 1 (first match wins).
        ("https://pubmed.ncbi.nlm.nih.gov/1/", (1, "primary_record")),
        ("https://mit.edu/news", (2, "academic")),
        ("https://openalex.org/works/W1", (2, "academic")),
        ("https://en.wikipedia.org/wiki/X", (3, "reference")),
        ("https://apnews.com/article/1", (3, "journalism")),
        ("https://snopes.com/fact-check/x", (3, "fact_check_org")),
        ("https://medium.com/@a/story", (4, "opinion_commentary")),
        ("https://www.tiktok.com/@a/video/1", (5, "social_media")),
        ("https://unknown.example.com/x", (4, "opinion_commentary")),
        ("https://sub.example.co.uk/deep", (4, "opinion_commentary")),
        ("not a url", (4, "opinion_commentary")),
    ]
    for url, (tier, cls) in cases:
        match = classify_url(url, rules)
        assert (match.tier, match.source_class.value) == (tier, cls), url


def test_verify_excerpt_cases() -> None:
    """T07.031: exact, quotes, wrapping, dashes, invented, too short."""
    doc = "First line.\nThe “quick” brown fox — jumped — over the lazy dog.\nLast line."
    assert verify_excerpt(doc, "The “quick” brown fox — jumped — over the lazy dog.") == (
        True, 100.0)
    assert verify_excerpt(doc, 'The "quick" brown fox - jumped - over the lazy dog.') == (
        True, 100.0)
    assert verify_excerpt(doc, "over the lazy dog. Last line.") == (True, 100.0)
    invented, score = verify_excerpt(doc, "Zebras pilot helicopters over the moon daily.")
    assert invented is False and score < 90.0
    assert verify_excerpt(doc, "Too short.") == (False, 0.0)
    assert verify_excerpt(doc, "   ") == (False, 0.0)


def test_trim_passages() -> None:
    """T07.032: the claim-rich paragraph survives; order kept; cap honored."""
    filler_a = "The weather was mild and the streets were quiet that evening."
    gold = "Divorce rates hit fifty percent in the nineteen eighties census data."
    filler_b = "She bought bread and cheese at the corner market on Tuesday."
    doc = "\n\n".join([filler_a, gold, filler_b])
    trimmed = trim_passages(doc, "divorce rates fifty percent", ["the percentage"])
    assert gold in trimmed
    assert filler_a in trimmed or filler_b in trimmed  # budget allows company
    tiny = trim_passages(doc, "divorce rates fifty percent", ["the percentage"],
                         max_tokens=20)
    assert tiny == gold  # only the best fits
    assert trim_passages("", "claim", []) == ""
    # Survivors keep document order even when scores disagree.
    first = "Census data shows divorce rates clearly and directly here."
    doc2 = "\n\n".join([gold, filler_a, first])
    ordered = trim_passages(doc2, "divorce rates census data", ["rates"], max_tokens=40)
    assert ordered.index(gold) < ordered.index(first)
