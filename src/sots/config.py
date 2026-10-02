"""Settings loading (P00 T00.041).

``load_settings`` reads ``config/settings.yaml`` into a frozen Pydantic model
tree and overlays secrets from the environment (optionally via a ``.env``
file). Secrets never live in YAML (04 §1). Any missing file, missing key, or
validation failure raises :class:`ConfigError`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, ValidationError

from sots.errors import ConfigError


class FrozenModel(BaseModel):
    """Base model: immutable and tolerant of unknown future keys."""

    model_config = ConfigDict(frozen=True, extra="ignore")


class PathsSettings(FrozenModel):
    """Filesystem layout (02 §4)."""

    data_dir: str
    db_path: str
    inbox_dir: str
    cache_dir: str
    runs_dir: str
    logs_dir: str
    exports_dir: str
    profile_dir: str
    supplements_dir: str
    prompts_dir: str
    eval_dir: str
    vault_dir: str


class MuseProviderSettings(FrozenModel):
    """Muse provider; placeholders resolved by the author (04 §1, 15 OI-03)."""

    base_url: str | None
    api_key_env: str
    model: str | None
    context_window: int | None
    supports_json_schema: bool | None
    supports_web_search: bool | None
    price_input_per_1k: float | None
    price_output_per_1k: float | None
    request_path: str | None = None
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    request_template: dict | None = None
    response_text_path: str | None = None
    response_input_tokens_path: str | None = None
    response_output_tokens_path: str | None = None
    response_model_path: str | None = None


class LocalProviderSettings(FrozenModel):
    """Local Ollama provider (04 §1.2)."""

    base_url: str
    model: str | None
    num_ctx: int
    context_window: int
    price_input_per_1k: float
    price_output_per_1k: float


class ProvidersSettings(FrozenModel):
    """Provider block (04 §1)."""

    muse: MuseProviderSettings
    local: LocalProviderSettings


class ChunkTargetTokens(FrozenModel):
    """Per-provider chunk targets (04 §5)."""

    local: int
    muse: int


class ChunkSettings(FrozenModel):
    """Chunking (04 §5)."""

    target_tokens: ChunkTargetTokens
    overlap_tokens: int


class ContextBudgets(FrozenModel):
    """Per-piece context-pack token budgets (04 §4)."""

    book_profile: int
    chapter_brief: int
    core_messages: int
    author_profile: int
    document_summary: int
    neighbours: int
    supplements: int
    style_guide: int
    issue_context: int
    persona_card: int
    journey_spec: int
    f1_book: int
    f2_chapter: int
    f3_block: int
    f4_anchors: int
    f5_voice: int
    f6_arc: int


class ContextSettings(FrozenModel):
    """Context packs (04 §4)."""

    budgets: ContextBudgets


class BudgetSettings(FrozenModel):
    """Run budget and cost guards (04 §6)."""

    max_tokens_per_run: int
    max_cost_per_run: float | None
    warn_at: float


class CacheSettings(FrozenModel):
    """Cache behaviour (04 §2, 06 §3.2)."""

    fetch_ttl_days: int


class ConcurrencySettings(FrozenModel):
    """Provider semaphores and batch size (02 §7)."""

    muse: int
    local: int
    batch_size: int


class SearchSettings(FrozenModel):
    """Web search providers in order (04 §7, 16 §3)."""

    providers: list[str]
    searxng_base_url: str = "http://localhost:8888"


class ResearchSettings(FrozenModel):
    """Research limits (06 §3)."""

    max_urls_per_unit: int


class ClassifySettings(FrozenModel):
    """Classification review threshold (05 §3.4)."""

    review_threshold: float


class ExpandSettings(FrozenModel):
    """Expansion team limits (11)."""

    auto_approve_budget_tokens: int
    min_relevance: float
    leads_per_round: int


class RewritePassSettings(FrozenModel):
    """One rewrite pass: edit budget and review flag (19 §1)."""

    edit_budget: float
    author_review: bool = False


class RewriteSettings(FrozenModel):
    """Rewrite passes A and B (19 §3-§4)."""

    pass_a: RewritePassSettings
    pass_b: RewritePassSettings


class LanguageToolSettings(FrozenModel):
    """Local LanguageTool server (19 §2.1)."""

    url: str
    language: str


class ProposalDeskSettings(FrozenModel):
    """Proposal desk limits (18 §4)."""

    max_open: int


class DiscoverySettings(FrozenModel):
    """Discovery scouting limits (06 §9.3)."""

    max_candidates_per_chapter: int


class AudienceSettings(FrozenModel):
    """Audience lab sampling and panel guards (20)."""

    samples_per_persona: int
    min_panel_sd: float


class LegalSettings(FrozenModel):
    """Legal chamber jurisdictions (22 §3)."""

    primary_jurisdiction: str
    secondary_jurisdictions: list[str]


class PrivacySettings(FrozenModel):
    """Privacy flags (15 OI-06)."""

    personal_to_cloud: bool


class SafetySettings(FrozenModel):
    """Safety scan flags (01 R-PSY-04)."""

    scan_enabled: bool
    resources_file: str


class FetchSettings(FrozenModel):
    """Fetch politeness (06 §3.2, 16 F14)."""

    per_domain_rate_limit_per_s: float
    timeout_s: int


class CanarySettings(FrozenModel):
    """Run-guard canary (16 F19)."""

    enabled: bool
    threshold_words: int


class VaultSettings(FrozenModel):
    """Obsidian-vault mirror (OI-42, author-approved addition)."""

    enabled: bool
    author_notes_heading: str
    index_note: str


class AgentsSettings(FrozenModel):
    """Agent runtime knobs (16)."""

    max_observation_chars: int
    tool_timeout_s: int
    injection_patterns: list[str]


class Secrets(FrozenModel):
    """Secrets overlaid from the environment; never stored in YAML (04 §1)."""

    muse_api_key: str | None = None
    muse_base_url: str | None = None
    tavily_api_key: str | None = None
    courtlistener_token: str | None = None
    google_factcheck_key: str | None = None
    tmdb_api_key: str | None = None
    contact_email: str | None = None


class Settings(FrozenModel):
    """Full frozen settings tree mirroring ``config/settings.yaml``."""

    paths: PathsSettings
    providers: ProvidersSettings
    chunk: ChunkSettings
    context: ContextSettings
    budget: BudgetSettings
    cache: CacheSettings
    concurrency: ConcurrencySettings
    search: SearchSettings
    research: ResearchSettings
    classify: ClassifySettings
    expand: ExpandSettings
    rewrite: RewriteSettings
    languagetool: LanguageToolSettings
    proposal_desk: ProposalDeskSettings
    discovery: DiscoverySettings
    audience: AudienceSettings
    legal: LegalSettings
    privacy: PrivacySettings
    safety: SafetySettings
    fetch: FetchSettings
    canary: CanarySettings
    vault: VaultSettings
    agents: AgentsSettings
    words_per_page: int
    secrets: Secrets = Secrets()


#: Environment variable name -> Secrets field name (see .env.example).
ENV_SECRET_MAP: dict[str, str] = {
    "MUSE_API_KEY": "muse_api_key",
    "MUSE_BASE_URL": "muse_base_url",
    "TAVILY_API_KEY": "tavily_api_key",
    "COURTLISTENER_TOKEN": "courtlistener_token",
    "GOOGLE_FACTCHECK_KEY": "google_factcheck_key",
    "TMDB_API_KEY": "tmdb_api_key",
    "CONTACT_EMAIL": "contact_email",
}


def _read_env(env_file: Path | str | None) -> dict[str, str | None]:
    """Merge ``env_file`` values under real environment variables."""
    merged: dict[str, str | None] = {}
    if env_file is not None:
        env_path = Path(env_file)
        if env_path.is_file():
            merged.update(dotenv_values(env_path))
    for key in ENV_SECRET_MAP:
        if key in os.environ:
            merged[key] = os.environ[key]
    return merged


def load_settings(
    config_dir: Path | str = "config",
    env_file: Path | str | None = ".env",
) -> Settings:
    """Load and validate settings from ``config_dir/settings.yaml``.

    Args:
        config_dir: Directory containing ``settings.yaml``.
        env_file: Optional dotenv file with secrets; the real environment
            always wins over values from this file.

    Raises:
        ConfigError: If the file is missing/unparseable or a required key
            is missing or invalid.
    """
    settings_path = Path(config_dir) / "settings.yaml"
    if not settings_path.is_file():
        raise ConfigError(f"settings file not found: {settings_path}")
    try:
        raw: Any = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"cannot parse {settings_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{settings_path} must parse to a mapping")

    env = _read_env(env_file)
    secrets = {
        field: (value if value not in (None, "") else None)
        for var, field in ENV_SECRET_MAP.items()
        for value in [env.get(var)]
    }
    raw["secrets"] = secrets

    # A muse base URL from the environment fills the YAML placeholder (04 §1).
    if secrets["muse_base_url"] and isinstance(raw.get("providers"), dict):
        muse_cfg = raw["providers"].get("muse")
        if isinstance(muse_cfg, dict) and not muse_cfg.get("base_url"):
            muse_cfg["base_url"] = secrets["muse_base_url"]

    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid settings in {settings_path}: {exc}") from exc
