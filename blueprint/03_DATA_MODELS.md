# 03 — DATA MODELS

Every model is Pydantic v2 and lives in `src/sots/models/`. The field names below are
**exact**. Every model has `model_config = ConfigDict(frozen=True, extra="forbid")`
unless marked *mutable*.

IDs are strings built as `<prefix>_<ulid>`, e.g. `unit_01J9...`. Use one helper,
`models/ids.py::new_id(prefix)`.

---

## 1. Enums (`models/enums.py`)

```python
class ContentType(StrEnum):
    PERSONAL_EXPERIENCE = "personal_experience"   # something that happened to the author
    PERSONAL_BELIEF     = "personal_belief"       # opinion, value, conviction
    NARRATIVE_DEVICE    = "narrative_device"      # metaphor, framing, transition, hook
    LESSON_ADVICE       = "lesson_advice"         # self-help takeaway addressed to the reader
    FACTUAL_CLAIM       = "factual_claim"         # a checkable statement about the world
    MEDIA_REFERENCE     = "media_reference"       # mention or retelling of a work
    QUESTION_REFLECTION = "question_reflection"   # rhetorical or open question

class ClaimKind(StrEnum):                         # only when content_type == FACTUAL_CLAIM
    STATISTIC          = "statistic"
    LEGAL_CASE         = "legal_case"
    HISTORICAL_EVENT   = "historical_event"
    ACADEMIC_FINDING   = "academic_finding"       # science, psychology, research results
    SOCIAL_MEDIA_CASE  = "social_media_case"      # viral post, influencer event, online story
    NEWS_EVENT         = "news_event"
    QUOTE_ATTRIBUTION  = "quote_attribution"      # "X said Y"
    GENERAL_FACT       = "general_fact"
    SCRIPTURE_QUOTE    = "scripture_quote"        # 25 §5
    SCRIPTURE_TERM     = "scripture_term"         # Greek/Hebrew meaning claims
    PATRISTIC_ATTRIBUTION = "patristic_attribution"
    EVIDENCE_GRADE     = "evidence_grade"         # a protocol's claimed evidence strength (25 §4)

class MediaKind(StrEnum):
    BOOK = "book"; FILM = "film"; TV = "tv"; MUSIC = "music"; GAME = "game"
    PODCAST = "podcast"; ART = "art"; OTHER = "other"

class Checkability(StrEnum):
    CHECKABLE      = "checkable"       # fully checkable against public sources
    PARTIAL        = "partial"         # contains checkable parts inside personal framing
    NOT_CHECKABLE  = "not_checkable"   # personal, opinion, rhetorical

class SourceClass(StrEnum):            # WHAT KIND of truth a source provides
    PRIMARY_RECORD     = "primary_record"      # court record, government data, original dataset
    ACADEMIC           = "academic"            # peer-reviewed or scholarly
    REFERENCE          = "reference"           # encyclopedias, established databases
    JOURNALISM         = "journalism"          # established news organizations
    FACT_CHECK_ORG     = "fact_check_org"      # Snopes, PolitiFact, AP Fact Check, etc.
    OPINION_COMMENTARY = "opinion_commentary"  # blogs, op-eds, essays
    SOCIAL_MEDIA       = "social_media"        # posts, threads, videos, forums
    FICTIONAL_MEDIA    = "fictional_media"     # the work itself (film, novel, show, song)
    AUTHOR_SUPPLEMENT  = "author_supplement"   # files the author put in supplements/

class Verdict(StrEnum):                # HOW TRUE (ordered strongest → weakest)
    TRUE           = "true"
    MOSTLY_TRUE    = "mostly_true"
    PARTIALLY_TRUE = "partially_true"
    MISLEADING     = "misleading"
    FALSE          = "false"
    UNSUPPORTED    = "unsupported"     # searched, nothing solid found either way
    UNVERIFIABLE   = "unverifiable"    # cannot be verified by its nature/access
    NOT_CHECKABLE  = "not_checkable"   # personal/opinion (R-TRUTH-05)
    FAILED         = "failed"          # pipeline error

class Stance(StrEnum):
    SUPPORTS = "supports"; CONTRADICTS = "contradicts"; MIXED = "mixed"; CONTEXT = "context"

class Severity(StrEnum):
    INFO = "info"; LOW = "low"; MEDIUM = "medium"; HIGH = "high"

class StageStatus(StrEnum):
    PENDING = "pending"; RUNNING = "running"; DONE = "done"; FAILED = "failed"; SKIPPED = "skipped"
```

## 2. Documents and units

```python
class Document(BaseModel):
    id: str                     # doc_...
    source_path: str            # original path the author gave
    inbox_path: str             # immutable copy in data/inbox/
    sha256: str
    title: str
    chapter_id: str | None      # e.g. "ch03", links to profile/chapters/ch03_brief.md
    char_count: int
    word_count: int
    ingested_at: datetime

class Chunk(BaseModel):
    id: str                     # chk_...
    document_id: str
    index: int
    start_char: int
    end_char: int
    token_estimate: int

class Unit(BaseModel):          # *mutable*: classification fields are filled in stage 3
    id: str                     # unit_...
    document_id: str
    chunk_id: str
    run_id: str
    order: int                  # position in document
    text: str                   # exact author words (substring of document)
    start_char: int
    end_char: int
    content_type: ContentType | None = None
    claim_kind: ClaimKind | None = None
    media_kind: MediaKind | None = None
    checkability: Checkability | None = None
    entities: list[str] = []    # people, orgs, works, places, cases named
    normalized_claim: str | None = None   # the claim restated neutrally and self-contained
    classify_confidence: float | None = None
    safety_flag: bool = False
    parent_unit_id: str | None = None     # set for embedded claims (05 §3.3)
    block: int | None = None              # 1–6, the brief block (23 §5)
    prompt_id: str | None = None          # e.g. "ch03.B2.P1"
    anchor_ids: list[str] = []            # anchors from profile/anchors.yaml mentioned in the unit
    labeled_by: Literal["model", "author"] = "model"
```

## 3. Evidence and verdicts

```python
class Evidence(BaseModel):
    id: str                     # ev_...
    unit_id: str
    url: str
    title: str
    publisher: str | None
    published_date: date | None
    accessed_at: datetime
    source_class: SourceClass
    tier: int                   # 1 (strongest) … 5 (weakest), from source_tiers.yaml
    excerpt: str                # verbatim text found in the fetched page
    excerpt_match_score: float  # rapidfuzz score, must be ≥ 90 (R-TRUTH-02)
    stance: Stance
    fetcher: str                # which fetcher produced it
    content_hash: str           # hash of the fetched page text (stored in cache)

class RuleCheck(BaseModel):
    rule_id: str                # e.g. "VR-STAT-01"
    passed: bool
    cap: Verdict | None         # the verdict ceiling this rule imposes if failed
    note: str

class VerdictRecord(BaseModel):
    id: str                     # vd_...
    unit_id: str
    run_id: str
    proposed_verdict: Verdict   # from the adjudicator (LLM)
    final_verdict: Verdict      # after rules.py caps (R-TRUTH-03)
    truth_basis: SourceClass | None   # the class of the strongest supporting evidence
    confidence: float           # 0–1, see 06_FACT_CHECK_PROTOCOL §7
    evidence_ids: list[str]
    researcher_summary: str
    skeptic_objections: list[str]
    adjudicator_reasoning: str
    rule_checks: list[RuleCheck]
    what_is_accurate: str       # the part the author got right
    what_is_off: str            # the part that is wrong/overstated ("" if none)
    suggested_correction: str | None   # neutral corrected wording, NOT styled prose
    claim_specific: dict        # structured fields per claim_kind (06 §5)
    epistemic_tier: str | None = None          # DF | PT | IE | DEBUNKED | HEDGE (25 §1–2)
    tier_claimed_by_author: str | None = None  # from the dictation/brief tag, if any
```

## 4. Media

```python
class MediaWork(BaseModel):
    id: str                     # work_...
    kind: MediaKind
    title: str
    creators: list[str]         # author/director/showrunner/artist
    year: int | None
    external_ids: dict[str, str]   # e.g. {"tmdb": "...", "openlibrary": "...", "musicbrainz": "..."}
    resolved: bool              # False if the work could not be identified

class MediaPoint(BaseModel):
    statement: str              # one thing the author says about the work
    point_type: Literal["plot_fact", "quote", "attribution", "character", "detail"]
    accuracy: Literal["accurate", "partly_accurate", "inaccurate", "unverifiable"]
    correction: str | None
    evidence_ids: list[str]

class MediaCheck(BaseModel):
    id: str                     # mc_...
    unit_id: str
    run_id: str
    work: MediaWork
    points: list[MediaPoint]
    author_reading: str         # what the author says the work means
    established_readings: list[str]   # creator intent / critical consensus, sourced
    interpretation_status: Literal[
        "supported_reading",        # matches creator intent or critical consensus
        "plausible_personal_reading", # defensible but the author's own
        "contested_reading",        # critics disagree
        "contradicted_by_source",   # the work or its creator says otherwise
    ]
    message_alignment: float    # 0–1: how well the author's use fits the work's message
    use_in_book_note: str       # does this reference actually serve the book's point?
```

## 5. Psyche engines

```python
class EngineFinding(BaseModel):
    id: str                     # pf_...
    run_id: str
    engine: str                 # "emotion" | "cognitive" | "theme" | "archetype" | "blindspot" | "reader"
    finding_type: str           # engine-specific vocabulary (see 08)
    unit_ids: list[str]         # evidence in the author's text (at least 1)
    summary: str
    detail: str
    confidence: float
    severity: Severity
    responds_to: list[str] = [] # ids of findings from other engines this builds on
    question_for_author: str | None   # required for blindspot (R-PSY-03)

class Synthesis(BaseModel):
    run_id: str
    agreements: list[str]       # where engines converge
    tensions: list[str]         # where engines disagree
    top_insights: list[str]     # max 7, each citing finding ids
    finding_ids: list[str]
```

## 6. Narrative and voice

```python
class CoreMessage(BaseModel):
    id: str                     # "M1", "M2"… from profile/messages.yaml
    level: Literal["book", "chapter"]
    chapter_id: str | None
    statement: str
    priority: int               # 1 = most important

class MessageMapping(BaseModel):
    unit_id: str
    message_id: str | None      # None = serves no core message (possible drift)
    role: Literal["states", "illustrates", "supports_with_evidence", "counters", "transitions", "none"]
    strength: float             # 0–1

class DriftReport(BaseModel):
    run_id: str
    document_id: str
    coverage: dict[str, float]  # message_id → share of units serving it
    unmapped_ratio: float
    drift_segments: list[tuple[int, int]]   # unit order ranges that wander off
    missing_messages: list[str] # chapter messages never stated or illustrated
    flow_breaks: list[str]      # unit ids where the logic or emotion jumps without a bridge

class VoiceFingerprint(BaseModel):
    source: Literal["voice_corpus", "document"]   # voice_corpus = profile/voice_corpus/ (29); replaces style_samples
    avg_sentence_len: float
    sentence_len_stdev: float
    type_token_ratio: float
    punctuation_profile: dict[str, float]   # per 1000 words
    person_ratio: dict[str, float]          # first/second/third person pronoun shares
    signature_phrases: list[str]
    llm_style_description: str

class VoiceComparison(BaseModel):
    run_id: str
    document_id: str
    similarity: float           # 0–1
    deviations: list[str]
    off_voice_unit_ids: list[str]
```

## 7. Shadow Self

```python
class ShadowItem(BaseModel):
    category: Literal["contradiction", "avoidance", "self_serving_frame",
                      "unearned_lesson", "harshness_asymmetry", "fact_risk", "overreach"]
    unit_ids: list[str]
    observation: str
    question_for_author: str
    severity: Severity

class RubricScore(BaseModel):
    criterion_id: str           # from config/rubrics.yaml
    score: int                  # 1–5
    measured_value: float | None   # the metric behind the score, when it is measurable
    target: float | None
    met: bool
    justification: str
    unit_ids: list[str]

class ShadowReport(BaseModel):
    id: str                     # sh_...
    run_id: str
    document_id: str
    items: list[ShadowItem]
    scores: list[RubricScore]
    overall: float              # weighted mean, 1–5
    goals_met: int
    goals_total: int
    trend_vs_previous: dict[str, float]   # criterion_id → delta vs the last run on the same chapter
```

## 8. Profile

```python
class AuthorProfile(BaseModel):
    name_or_pen_name: str
    background: str
    why_this_book: str
    lived_experience_areas: list[str]
    sensitive_topics: list[str]      # handle gently, never skip checking
    values: list[str]
    known_biases_self_reported: list[str]

class BookProfile(BaseModel):
    working_title: str
    genre: Literal["self_help_reflective"]
    premise: str
    target_reader: str
    promise_to_reader: str          # what the reader gains
    tone_goals: list[str]
    out_of_scope: list[str]

class ChapterBrief(BaseModel):
    chapter_id: str                 # "ch01"
    title: str
    purpose: str
    key_messages: list[str]
    planned_stories: list[str]
    planned_references: list[str]   # facts, cases, media the author intends to use
    reader_takeaway: str
    raw_brief: str                  # the author's original brief text
```

> **Superseded (2026-09-28):** `ChapterBrief` is now defined in `23_BOOK_FOUNDATION.md §2`
> (6 blocks, dictation prompts, anchors, protocols). `AuthorProfile`/`BookProfile` fields
> follow `profile/author.md` and `profile/book.md`.
>
> The profile model fields are **provisional**. They will be finalized after the author
> provides the chapter briefs (see `15_OPEN_ITEMS.md`).

## 9. Runs and LLM calls

```python
class Run(BaseModel):               # *mutable*
    id: str
    document_ids: list[str]
    started_at: datetime
    finished_at: datetime | None
    stage_status: dict[str, StageStatus]
    budget_tokens: int
    used_tokens: int
    cost_estimate: float
    config_snapshot: dict           # settings + routing at run start

class LLMCall(BaseModel):
    id: str
    run_id: str | None
    task: str                       # routing key, e.g. "verify.skeptic"
    provider: str
    model: str
    prompt_id: str
    prompt_version: int
    input_hash: str
    input_tokens: int
    output_tokens: int
    cost_estimate: float
    latency_ms: int
    status: Literal["ok", "cached", "invalid_retry", "failed"]
    created_at: datetime
```
