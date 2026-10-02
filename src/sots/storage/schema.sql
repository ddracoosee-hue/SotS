-- SotS storage schema (P01 T01.030), SQLite + WAL.
-- One table per persisted model; list/dict/nested fields are JSON TEXT columns.
-- Scalar datetimes/dates/enums are stored as ISO TEXT; bools as INTEGER 0/1.
-- Mirrored by migrations/001_initial.sql at schema version 1.

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    inbox_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    title TEXT NOT NULL,
    chapter_id TEXT,
    char_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    "index" INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    token_estimate INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks (document_id);

CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    "order" INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    content_type TEXT,
    claim_kind TEXT,
    media_kind TEXT,
    checkability TEXT,
    entities TEXT NOT NULL,          -- JSON list[str]
    normalized_claim TEXT,
    classify_confidence REAL,
    safety_flag INTEGER NOT NULL DEFAULT 0,
    parent_unit_id TEXT,
    block INTEGER,
    prompt_id TEXT,
    anchor_ids TEXT NOT NULL,        -- JSON list[str]
    author_provenance TEXT,
    source_ref TEXT,
    serial TEXT,
    labeled_by TEXT NOT NULL DEFAULT 'model',
    revision_offsets TEXT NOT NULL   -- JSON dict[str, [int, int]]
);
CREATE INDEX IF NOT EXISTS idx_units_run ON units (run_id);
CREATE INDEX IF NOT EXISTS idx_units_document ON units (document_id);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    publisher TEXT,
    published_date TEXT,
    accessed_at TEXT NOT NULL,
    source_class TEXT NOT NULL,
    tier INTEGER NOT NULL,
    excerpt TEXT NOT NULL,
    excerpt_match_score REAL NOT NULL,
    stance TEXT NOT NULL,
    fetcher TEXT NOT NULL,
    content_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_unit ON evidence (unit_id);

CREATE TABLE IF NOT EXISTS fetched_docs (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    publisher TEXT,
    published_date TEXT,
    text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fetcher TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fetched_docs_hash ON fetched_docs (content_hash);

CREATE TABLE IF NOT EXISTS search_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    rank INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_search_hits_url ON search_hits (url);

CREATE TABLE IF NOT EXISTS verdict_records (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    proposed_verdict TEXT NOT NULL,
    final_verdict TEXT NOT NULL,
    truth_basis TEXT,
    confidence REAL NOT NULL,
    evidence_ids TEXT NOT NULL,      -- JSON list[str]
    researcher_summary TEXT NOT NULL,
    skeptic_objections TEXT NOT NULL, -- JSON list[str]
    adjudicator_reasoning TEXT NOT NULL,
    rule_checks TEXT NOT NULL,       -- JSON list[RuleCheck]
    what_is_accurate TEXT NOT NULL,
    what_is_off TEXT NOT NULL,
    suggested_correction TEXT,
    claim_specific TEXT NOT NULL,    -- JSON dict
    epistemic_tier TEXT,
    tier_claimed_by_author TEXT
);
CREATE INDEX IF NOT EXISTS idx_verdicts_run ON verdict_records (run_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_unit ON verdict_records (unit_id);

CREATE TABLE IF NOT EXISTS discovery_notes (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    why_interesting TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_discovery_unit ON discovery_notes (unit_id);

CREATE TABLE IF NOT EXISTS specialist_findings (
    unit_id TEXT NOT NULL,
    specialist TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,      -- JSON list[str]
    claim_specific TEXT NOT NULL,    -- JSON dict
    PRIMARY KEY (unit_id, specialist)
);

CREATE TABLE IF NOT EXISTS media_works (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    creators TEXT NOT NULL,          -- JSON list[str]
    year INTEGER,
    external_ids TEXT NOT NULL,      -- JSON dict[str, str]
    resolved INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS media_checks (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    work TEXT NOT NULL,              -- JSON MediaWork
    points TEXT NOT NULL,            -- JSON list[MediaPoint]
    author_reading TEXT NOT NULL,
    established_readings TEXT NOT NULL, -- JSON list[str]
    interpretation_status TEXT NOT NULL,
    message_alignment REAL NOT NULL,
    use_in_book_note TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_media_checks_run ON media_checks (run_id);
CREATE INDEX IF NOT EXISTS idx_media_checks_unit ON media_checks (unit_id);

CREATE TABLE IF NOT EXISTS engine_findings (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    engine TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    summary TEXT NOT NULL,
    detail TEXT NOT NULL,
    confidence REAL NOT NULL,
    severity TEXT NOT NULL,
    responds_to TEXT NOT NULL,       -- JSON list[str]
    question_for_author TEXT
);
CREATE INDEX IF NOT EXISTS idx_engine_findings_run ON engine_findings (run_id);

CREATE TABLE IF NOT EXISTS syntheses (
    run_id TEXT PRIMARY KEY,
    agreements TEXT NOT NULL,        -- JSON list[str]
    tensions TEXT NOT NULL,          -- JSON list[str]
    top_insights TEXT NOT NULL,      -- JSON list[str]
    finding_ids TEXT NOT NULL        -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS core_messages (
    id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    chapter_id TEXT,
    statement TEXT NOT NULL,
    priority INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_core_messages_chapter ON core_messages (chapter_id);

CREATE TABLE IF NOT EXISTS message_mappings (
    unit_id TEXT PRIMARY KEY,
    message_id TEXT,
    role TEXT NOT NULL,
    strength REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS drift_reports (
    run_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    coverage TEXT NOT NULL,          -- JSON dict[str, float]
    unmapped_ratio REAL NOT NULL,
    drift_segments TEXT NOT NULL,    -- JSON list[[int, int]]
    missing_messages TEXT NOT NULL,  -- JSON list[str]
    flow_breaks TEXT NOT NULL,       -- JSON list[str]
    PRIMARY KEY (run_id, document_id)
);

CREATE TABLE IF NOT EXISTS voice_fingerprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    avg_sentence_len REAL NOT NULL,
    sentence_len_stdev REAL NOT NULL,
    type_token_ratio REAL NOT NULL,
    punctuation_profile TEXT NOT NULL, -- JSON dict[str, float]
    person_ratio TEXT NOT NULL,        -- JSON dict[str, float]
    signature_phrases TEXT NOT NULL,   -- JSON list[str]
    llm_style_description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_comparisons (
    run_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    similarity REAL NOT NULL,
    deviations TEXT NOT NULL,        -- JSON list[str]
    off_voice_unit_ids TEXT NOT NULL, -- JSON list[str]
    PRIMARY KEY (run_id, document_id)
);

CREATE TABLE IF NOT EXISTS shadow_reports (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    items TEXT NOT NULL,             -- JSON list[ShadowItem]
    scores TEXT NOT NULL,            -- JSON list[RubricScore]
    overall REAL NOT NULL,
    goals_met INTEGER NOT NULL,
    goals_total INTEGER NOT NULL,
    trend_vs_previous TEXT NOT NULL  -- JSON dict[str, float]
);
CREATE INDEX IF NOT EXISTS idx_shadow_reports_run ON shadow_reports (run_id);
CREATE INDEX IF NOT EXISTS idx_shadow_reports_document ON shadow_reports (document_id);

CREATE TABLE IF NOT EXISTS author_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_or_pen_name TEXT NOT NULL,
    background TEXT NOT NULL,
    why_this_book TEXT NOT NULL,
    lived_experience_areas TEXT NOT NULL,   -- JSON list[str]
    sensitive_topics TEXT NOT NULL,         -- JSON list[str]
    "values" TEXT NOT NULL,                 -- JSON list[str]
    known_biases_self_reported TEXT NOT NULL -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS book_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    working_title TEXT NOT NULL,
    genre TEXT NOT NULL,
    premise TEXT NOT NULL,
    target_reader TEXT NOT NULL,
    promise_to_reader TEXT NOT NULL,
    tone_goals TEXT NOT NULL,        -- JSON list[str]
    out_of_scope TEXT NOT NULL,      -- JSON list[str]
    media_exclusions TEXT NOT NULL   -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS chapter_briefs (
    chapter_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    purpose TEXT NOT NULL,
    key_messages TEXT NOT NULL,      -- JSON list[str]
    planned_stories TEXT NOT NULL,   -- JSON list[str]
    planned_references TEXT NOT NULL, -- JSON list[str]
    reader_takeaway TEXT NOT NULL,
    raw_brief TEXT NOT NULL,
    reader_journey TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    document_ids TEXT NOT NULL,      -- JSON list[str]
    started_at TEXT NOT NULL,
    finished_at TEXT,
    stage_status TEXT NOT NULL,      -- JSON dict[str, StageStatus]
    budget_tokens INTEGER NOT NULL,
    used_tokens INTEGER NOT NULL,
    cost_estimate REAL NOT NULL,
    config_snapshot TEXT NOT NULL    -- JSON dict
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    task TEXT NOT NULL,
    provider TEXT NOT NULL,
    "model" TEXT NOT NULL,
    prompt_id TEXT NOT NULL,
    prompt_version INTEGER NOT NULL,
    input_hash TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_estimate REAL NOT NULL,
    latency_ms INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    fallback_used INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_run ON llm_calls (run_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_status ON llm_calls (status);

CREATE TABLE IF NOT EXISTS chapter_state (
    chapter_id TEXT PRIMARY KEY,
    act INTEGER NOT NULL,
    gate_status TEXT NOT NULL,       -- JSON dict[str, str]
    blocked_reasons TEXT NOT NULL    -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    definition TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    chapter_ids TEXT NOT NULL,       -- JSON list[str]
    message_ids TEXT NOT NULL,       -- JSON list[str]
    maturity TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    rationale TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    inferred INTEGER NOT NULL,
    PRIMARY KEY (source_id, target_id, relation)
);

CREATE TABLE IF NOT EXISTS concept_graphs (
    run_id TEXT PRIMARY KEY,
    concepts TEXT NOT NULL,          -- JSON list[Concept]
    edges TEXT NOT NULL,             -- JSON list[ConceptEdge]
    hubs TEXT NOT NULL,              -- JSON list[str]
    bridges TEXT NOT NULL,           -- JSON list[str]
    orphans TEXT NOT NULL            -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS expansion_threads (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    concept_ids TEXT NOT NULL,       -- JSON list[str]
    message_ids TEXT NOT NULL,       -- JSON list[str]
    rationale TEXT NOT NULL,
    estimated_tokens INTEGER NOT NULL,
    status TEXT NOT NULL,
    critic_score REAL
);
CREATE INDEX IF NOT EXISTS idx_expansion_threads_status ON expansion_threads (status);

CREATE TABLE IF NOT EXISTS research_briefs (
    thread_id TEXT PRIMARY KEY,
    central_question TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    author_starting_point TEXT NOT NULL, -- JSON list[str]
    sub_questions TEXT NOT NULL,         -- JSON list[str]
    must_find TEXT NOT NULL,             -- JSON list[str]
    exclusions TEXT NOT NULL,            -- JSON list[str]
    max_depth INTEGER NOT NULL,
    max_sources INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS research_notes (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    sub_question TEXT NOT NULL,
    claim TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    depth INTEGER NOT NULL,
    novelty REAL NOT NULL,
    leads TEXT NOT NULL            -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_research_notes_thread ON research_notes (thread_id);

CREATE TABLE IF NOT EXISTS deep_research_reports (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    title TEXT NOT NULL,
    executive_summary TEXT NOT NULL, -- JSON list[ReportStatement]
    sections TEXT NOT NULL,          -- JSON list[ReportSection]
    counter_perspectives TEXT NOT NULL, -- JSON ReportSection
    connections_to_author_text TEXT NOT NULL, -- JSON ReportSection
    new_concepts TEXT NOT NULL,      -- JSON list[Concept]
    open_questions TEXT NOT NULL,    -- JSON list[str]
    source_mix TEXT NOT NULL,        -- JSON dict[str, int]
    saturation_curve TEXT NOT NULL   -- JSON list[float]
);
CREATE INDEX IF NOT EXISTS idx_deep_reports_thread ON deep_research_reports (thread_id);

CREATE TABLE IF NOT EXISTS margin_notes (
    id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    origin TEXT NOT NULL,
    links TEXT NOT NULL,             -- JSON list[str]
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_margin_notes_unit ON margin_notes (unit_id);
CREATE INDEX IF NOT EXISTS idx_margin_notes_status ON margin_notes (status);

CREATE TABLE IF NOT EXISTS integration_briefs (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    placements TEXT NOT NULL,        -- JSON list[dict]
    new_message_candidates TEXT NOT NULL, -- JSON list[str]
    restructure_suggestions TEXT NOT NULL, -- JSON list[str]
    questions_for_author TEXT NOT NULL,    -- JSON list[str]
    risks TEXT NOT NULL              -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_integration_briefs_chapter ON integration_briefs (chapter_id);

CREATE TABLE IF NOT EXISTS critic_scores (
    target_id TEXT PRIMARY KEY,
    relevance REAL NOT NULL,
    grounding REAL NOT NULL,
    novelty REAL NOT NULL,
    voice_respect REAL NOT NULL,
    balance REAL NOT NULL,
    verdict TEXT NOT NULL,
    reasons TEXT NOT NULL            -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS agent_cards (
    name TEXT PRIMARY KEY,
    team TEXT NOT NULL,
    role TEXT NOT NULL,
    prompts TEXT NOT NULL,           -- JSON AgentCardPrompts
    output_model TEXT NOT NULL,
    routing_task TEXT NOT NULL,
    tools TEXT NOT NULL,             -- JSON list[str]
    internet INTEGER NOT NULL,
    limits TEXT NOT NULL,            -- JSON AgentLimits
    grading TEXT NOT NULL,           -- JSON AgentGrading
    failsafes TEXT NOT NULL,         -- JSON list[str]
    foundation_pieces TEXT NOT NULL, -- JSON list[str]
    on_failure TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    team TEXT NOT NULL,
    act TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    steps INTEGER NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    cost REAL NOT NULL,
    status TEXT NOT NULL,
    failure_code TEXT,
    grade_attempts INTEGER NOT NULL,
    final_grade REAL,
    checkpoint_key TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_run ON agent_runs (run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs (status);

CREATE TABLE IF NOT EXISTS budget_slices (
    scope TEXT PRIMARY KEY,
    tokens_allowed INTEGER NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost_allowed REAL NOT NULL,
    cost_used REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS grade_records (
    id TEXT PRIMARY KEY,
    artifact_type TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    rubric_id TEXT NOT NULL,
    rubric_version INTEGER NOT NULL,
    criteria TEXT NOT NULL,          -- JSON list[CriterionResult]
    score REAL NOT NULL,
    passed INTEGER NOT NULL,
    feedback_for_generator TEXT NOT NULL, -- JSON list[str]
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grade_records_artifact ON grade_records (artifact_id);

CREATE TABLE IF NOT EXISTS grader_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_grades INTEGER NOT NULL,
    first_attempt_pass_rate REAL NOT NULL,
    author_reject_rate REAL NOT NULL,
    pass_within_max_rate REAL NOT NULL,
    tiebreak_rate REAL NOT NULL,
    too_lenient INTEGER NOT NULL,
    too_strict INTEGER NOT NULL,
    judge_disagreement INTEGER NOT NULL,
    top_rejection_reasons TEXT NOT NULL -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    title TEXT NOT NULL,
    pitch TEXT NOT NULL,
    what_was_found TEXT NOT NULL,    -- JSON list[ReportStatement]
    connects_to_units TEXT NOT NULL, -- JSON list[str]
    message_ids TEXT NOT NULL,       -- JSON list[str]
    media_work TEXT,                 -- JSON MediaWork | null
    placements TEXT NOT NULL,        -- JSON list[PlacementOption]
    modes TEXT NOT NULL,             -- JSON list[IntegrationMode]
    questions TEXT NOT NULL,         -- JSON list[AuthorQuestion]
    risks TEXT NOT NULL,             -- JSON list[str]
    grade_id TEXT NOT NULL,
    status TEXT NOT NULL,
    priority REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_proposals_run ON proposals (run_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals (status);

CREATE TABLE IF NOT EXISTS proposal_decisions (
    proposal_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    placement_id TEXT,
    mode_id TEXT,
    answers TEXT NOT NULL,           -- JSON dict[str, str]
    author_notes TEXT NOT NULL,
    reject_reason TEXT,
    decided_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integration_plan_items (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    placement TEXT NOT NULL,         -- JSON PlacementOption
    mode TEXT NOT NULL,              -- JSON IntegrationMode
    author_answers TEXT NOT NULL,    -- JSON dict[str, str]
    evidence_ids TEXT NOT NULL,      -- JSON list[str]
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_plan_items_chapter ON integration_plan_items (chapter_id);
CREATE INDEX IF NOT EXISTS idx_plan_items_status ON integration_plan_items (status);

CREATE TABLE IF NOT EXISTS revision_hunks (
    id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    before TEXT NOT NULL,
    after TEXT NOT NULL,
    before_span TEXT NOT NULL,       -- JSON [int, int]
    change_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    agent TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,      -- JSON list[str]
    legal_issue_ids TEXT NOT NULL,   -- JSON list[str]
    audience_brief_id TEXT,
    origin TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revision_hunks_revision ON revision_hunks (revision_id);
CREATE INDEX IF NOT EXISTS idx_revision_hunks_status ON revision_hunks (status);

CREATE TABLE IF NOT EXISTS revisions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chapter_id TEXT,
    pass_name TEXT NOT NULL,
    parent_revision_id TEXT,
    text_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    hunks TEXT NOT NULL,             -- JSON list[str]
    style_report_id TEXT,
    cross_check_report_id TEXT,
    gate_status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revisions_document ON revisions (document_id);
CREATE INDEX IF NOT EXISTS idx_revisions_chapter ON revisions (chapter_id);
CREATE INDEX IF NOT EXISTS idx_revisions_status ON revisions (gate_status);

CREATE TABLE IF NOT EXISTS style_guides (
    version INTEGER PRIMARY KEY,
    source_hash TEXT NOT NULL,
    voice_summary TEXT NOT NULL,
    dos TEXT NOT NULL,               -- JSON list[str]
    donts TEXT NOT NULL,             -- JSON list[str]
    protected_terms TEXT NOT NULL,   -- JSON list[str]
    intentional_patterns TEXT NOT NULL, -- JSON list[str]
    punctuation_habits TEXT NOT NULL, -- JSON dict[str, str]
    person_and_address TEXT NOT NULL,
    rhythm_targets TEXT NOT NULL,    -- JSON dict[str, float]
    examples TEXT NOT NULL           -- JSON list[str]
);

CREATE TABLE IF NOT EXISTS style_reports (
    id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    fingerprint_before TEXT NOT NULL, -- JSON VoiceFingerprint
    fingerprint_after TEXT NOT NULL,  -- JSON VoiceFingerprint
    voice_similarity REAL NOT NULL,
    per_hunk_similarity TEXT NOT NULL, -- JSON dict[str, float]
    protected_terms_intact REAL NOT NULL,
    drift_notes TEXT NOT NULL,       -- JSON list[str]
    tone_shift TEXT NOT NULL,        -- JSON dict[str, float]
    verdict TEXT NOT NULL,
    fix_requests TEXT NOT NULL      -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_style_reports_revision ON style_reports (revision_id);

CREATE TABLE IF NOT EXISTS cross_check_reports (
    id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    items TEXT NOT NULL,             -- JSON list[CrossCheckItem]
    pass_rate REAL NOT NULL,
    verdict TEXT NOT NULL,
    notes TEXT NOT NULL             -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_cross_check_reports_rev ON cross_check_reports (revision_id);

CREATE TABLE IF NOT EXISTS personas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL,
    life_stage TEXT NOT NULL,
    region TEXT NOT NULL,
    background_notes TEXT NOT NULL,
    reading_habits TEXT NOT NULL,
    need_for_cognition TEXT NOT NULL,
    current_season TEXT NOT NULL,
    skepticism TEXT NOT NULL,
    "values" TEXT NOT NULL,          -- JSON list[str]
    what_would_make_them_close_the_book TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mechanics_findings (
    id TEXT PRIMARY KEY,
    analyst TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    metric TEXT,
    value REAL,
    threshold REAL,
    issue TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    severity TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mechanics_revision ON mechanics_findings (revision_id);

CREATE TABLE IF NOT EXISTS persona_reactions (
    id TEXT PRIMARY KEY,
    persona_id TEXT NOT NULL,
    sample INTEGER NOT NULL,
    revision_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    first_impression TEXT NOT NULL,
    felt TEXT NOT NULL,              -- JSON list[str]
    recognition REAL NOT NULL,
    felt_judged REAL NOT NULL,
    curiosity REAL NOT NULL,
    absorption REAL NOT NULL,
    insight REAL NOT NULL,
    agency REAL NOT NULL,
    preachiness REAL NOT NULL,
    credibility REAL NOT NULL,
    intellectual_respect REAL NOT NULL,
    relatability REAL NOT NULL,
    would_continue REAL NOT NULL,
    would_share REAL NOT NULL,
    confusing_parts TEXT NOT NULL,   -- JSON list[QuoteRef]
    cringe_parts TEXT NOT NULL,      -- JSON list[QuoteRef]
    strongest_line TEXT,             -- JSON QuoteRef | null
    takeaway_in_own_words TEXT NOT NULL,
    disagreements TEXT NOT NULL,     -- JSON list[QuoteRef]
    question_for_author TEXT
);
CREATE INDEX IF NOT EXISTS idx_persona_reactions_revision ON persona_reactions (revision_id);

CREATE TABLE IF NOT EXISTS audience_scorecards (
    id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    metric_means TEXT NOT NULL,      -- JSON dict[str, float]
    cohort_means TEXT NOT NULL,      -- JSON dict[str, dict[str, float]]
    metric_sd TEXT NOT NULL,         -- JSON dict[str, float]
    metric_min TEXT NOT NULL,        -- JSON dict[str, float]
    metric_max TEXT NOT NULL,        -- JSON dict[str, float]
    message_reception_rate REAL NOT NULL,
    journey_curve TEXT NOT NULL,     -- JSON dict[str, list[float]]
    hotspots TEXT NOT NULL,          -- JSON list[str]
    strong_lines TEXT NOT NULL      -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_audience_scorecards_revision ON audience_scorecards (revision_id);

CREATE TABLE IF NOT EXISTS audience_briefs (
    id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    scorecard_id TEXT NOT NULL,
    priorities TEXT NOT NULL,        -- JSON list[BriefItem]
    do_not_touch TEXT NOT NULL,      -- JSON list[str]
    voice_cautions TEXT NOT NULL    -- JSON list[str]
);
CREATE INDEX IF NOT EXISTS idx_audience_briefs_revision ON audience_briefs (revision_id);

CREATE TABLE IF NOT EXISTS calibration (
    id TEXT PRIMARY KEY,
    metric TEXT NOT NULL,
    cohort TEXT NOT NULL,
    synthetic_mean REAL NOT NULL,
    real_mean REAL NOT NULL,
    bias REAL NOT NULL,
    correlation REAL,
    real_respondents INTEGER NOT NULL,
    unreliable INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS playbook (
    technique TEXT NOT NULL,
    cohort TEXT NOT NULL,
    metric TEXT NOT NULL,
    alpha REAL NOT NULL,
    beta REAL NOT NULL,
    trials INTEGER NOT NULL,
    PRIMARY KEY (technique, cohort, metric)
);

CREATE TABLE IF NOT EXISTS legal_issues (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    revision_id TEXT NOT NULL,
    unit_ids TEXT NOT NULL,          -- JSON list[str]
    issue_types TEXT NOT NULL,       -- JSON list[str]
    persons_involved TEXT NOT NULL,  -- JSON list[dict]
    preliminary_risk TEXT NOT NULL,
    assigned_counsel TEXT NOT NULL,  -- JSON list[str]
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_legal_issues_run ON legal_issues (run_id);
CREATE INDEX IF NOT EXISTS idx_legal_issues_status ON legal_issues (status);

CREATE TABLE IF NOT EXISTS positions (
    id TEXT PRIMARY KEY,
    issue_id TEXT NOT NULL,
    counsel TEXT NOT NULL,
    "round" INTEGER NOT NULL,
    stance TEXT NOT NULL,
    risk TEXT NOT NULL,
    argument TEXT NOT NULL,
    authorities TEXT NOT NULL,       -- JSON list[Authority]
    proposed_edits TEXT NOT NULL,    -- JSON list[dict]
    rebuttals TEXT NOT NULL,         -- JSON list[dict]
    argument_score REAL
);
CREATE INDEX IF NOT EXISTS idx_positions_issue ON positions (issue_id);

CREATE TABLE IF NOT EXISTS defense_memos (
    id TEXT PRIMARY KEY,
    issue_id TEXT NOT NULL,
    text_position TEXT NOT NULL,
    defense_basis TEXT NOT NULL,     -- JSON list[str]
    argument TEXT NOT NULL,
    required_edits TEXT NOT NULL,    -- JSON list[dict]
    residual_risk TEXT NOT NULL,
    answered_dissents TEXT NOT NULL, -- JSON list[dict]
    endorsements TEXT NOT NULL,      -- JSON dict[str, str]
    grade_id TEXT NOT NULL,
    needs_licensed_attorney INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_defense_memos_issue ON defense_memos (issue_id);

CREATE TABLE IF NOT EXISTS learning_changes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    before TEXT NOT NULL,
    after TEXT NOT NULL,
    evidence TEXT NOT NULL,
    status TEXT NOT NULL,
    applied_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_learning_changes_status ON learning_changes (status);

CREATE TABLE IF NOT EXISTS prompt_trials (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL,
    baseline_version INTEGER NOT NULL,
    candidate_version INTEGER NOT NULL,
    metric_deltas TEXT NOT NULL,     -- JSON dict[str, float]
    release_blocker_regressions TEXT NOT NULL, -- JSON list[str]
    promoted INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prompt_trials_prompt ON prompt_trials (prompt_id);

-- Infrastructure tables (02 section 5 / 16 failsafes).

CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    kind TEXT NOT NULL,
    unit_id TEXT,
    document_id TEXT,
    chapter_id TEXT,
    status TEXT,
    body TEXT NOT NULL,              -- JSON dict
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_summaries_run ON summaries (run_id);
CREATE INDEX IF NOT EXISTS idx_summaries_document ON summaries (document_id);
CREATE INDEX IF NOT EXISTS idx_summaries_unit ON summaries (unit_id);
CREATE INDEX IF NOT EXISTS idx_summaries_chapter ON summaries (chapter_id);
CREATE INDEX IF NOT EXISTS idx_summaries_status ON summaries (status);

CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS dead_letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    agent TEXT NOT NULL,
    team TEXT NOT NULL,
    payload TEXT NOT NULL,           -- JSON dict
    error TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dead_letters_run ON dead_letters (run_id);

CREATE TABLE IF NOT EXISTS checkpoints (
    key TEXT PRIMARY KEY,
    run_id TEXT,
    state TEXT NOT NULL,             -- JSON dict
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON checkpoints (run_id);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    type TEXT NOT NULL,
    payload TEXT NOT NULL,           -- JSON dict
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events (run_id);

CREATE TABLE IF NOT EXISTS dialogues (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    proposal_id TEXT,
    turns TEXT NOT NULL,             -- JSON list[dict]
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dialogues_run ON dialogues (run_id);
CREATE INDEX IF NOT EXISTS idx_dialogues_status ON dialogues (status);

CREATE TABLE IF NOT EXISTS waivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    issue_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_waivers_run ON waivers (run_id);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supplement_docs (
    path TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL,
    text TEXT NOT NULL,
    indexed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
