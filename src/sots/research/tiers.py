"""Source-tier classification (P07 T07.030, 06 §2).

fnmatch rules from `config/source_tiers.yaml`, first match wins, tried
against the host and each parent domain (`www.x.gov` matches `*.gov` and
`x.gov`). Unknown domains fall back to the file's default.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, ConfigDict

from sots.errors import ConfigError
from sots.models.enums import SourceClass


class TierRule(BaseModel):
    """One domain-pattern rule (06 §2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pattern: str
    tier: int
    source_class: SourceClass


class TierMatch(BaseModel):
    """A URL's tier verdict (06 §2)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tier: int
    source_class: SourceClass


class TierRules(BaseModel):
    """The loaded rules file (rules + default)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rules: list[TierRule]
    default: TierMatch


def load_tier_rules(path: str | Path) -> TierRules:
    """Parse source_tiers.yaml (author-editable, validated strictly)."""
    candidate = Path(path)
    if not candidate.is_file():
        raise ConfigError(f"tiers file not found: {candidate}")
    try:
        raw = yaml.safe_load(candidate.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse {candidate}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{candidate} must parse to a mapping")
    try:
        rules = [
            TierRule(
                pattern=entry["pattern"], tier=entry["tier"],
                source_class=SourceClass(entry["class"]),
            )
            for entry in raw.get("rules", [])
        ]
        default_raw = raw.get("default", {})
        default = TierMatch(
            tier=default_raw.get("tier", 4),
            source_class=SourceClass(default_raw.get("class", "opinion_commentary")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError(f"invalid tiers in {candidate}: {exc}") from exc
    return TierRules(rules=rules, default=default)


def _host_candidates(host: str) -> list[str]:
    """The host plus each parent domain, longest first."""
    labels = host.lower().split(".")
    return [".".join(labels[i:]) for i in range(len(labels))]


def classify_url(url: str, rules: TierRules) -> TierMatch:
    """First matching rule wins; no match returns the default (06 §2)."""
    host = urlparse(url.strip().lower()).netloc.split("@")[-1].split(":")[0]
    if not host:
        return rules.default
    candidates = _host_candidates(host)
    for rule in rules.rules:
        pattern = rule.pattern.lower()
        if any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates):
            return TierMatch(tier=rule.tier, source_class=rule.source_class)
    return rules.default
