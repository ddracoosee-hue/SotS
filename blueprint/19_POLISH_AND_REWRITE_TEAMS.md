# 19 — POLISH AND REWRITE TEAMS (Pass A: mid-process · Pass B: final master rewrite)

There are two rewrite teams. Both correct spelling, grammar, and formatting, and both must
keep the **author's personal tone**. Each team has a **Style Analyst** (voice reports) and its
sibling, the **Reference Cross-Checker** (accuracy of every fact, name, number, quote, and
citation). **The project does not move forward until both approve.**

| | Pass A — Mid Polish | Pass B — Master Rewrite |
|---|---|---|
| Act | II (after the Act I analysis) | VI (the final act) |
| Goal | A clean, corrected, *lightly* improved "Revised Draft" that the audience lab and legal team can evaluate | The final manuscript: accepted proposals woven in, legal edits applied, audience feedback applied, fully proofread |
| Edit budget | ≤ 15% of tokens changed per paragraph | ≤ 35% per paragraph (new woven passages excluded; they have their own checks) |
| Author review of changes | optional (setting) | **required** (accept/reject per hunk) |

---

## 1. Shared foundations

### 1.1 Revision model (`src/sots/models/rewrite.py`)

```python
class RevisionHunk(BaseModel):
    id: str                                  # hunk_...
    revision_id: str
    unit_ids: list[str]                      # the author's units this hunk touches
    before: str                              # exact text before
    after: str                               # proposed text
    before_span: tuple[int, int]             # offsets in the parent revision's text
    change_type: Literal["spelling", "grammar", "punctuation", "formatting", "clarity",
                         "flow", "fact_correction", "legal_edit", "audience_edit",
                         "woven_insert", "structure"]
    reason: str
    agent: str
    evidence_ids: list[str] = []             # required for fact_correction / woven_insert
    legal_issue_ids: list[str] = []          # required for legal_edit
    audience_brief_id: str | None = None     # required for audience_edit
    origin: Origin                           # AUTHOR text kept, or SYSTEM-generated
    status: Literal["proposed", "auto_applied", "accepted", "rejected", "reverted"]

class Revision(BaseModel):
    id: str                                  # rev_...
    document_id: str
    chapter_id: str | None
    pass_name: Literal["A", "A_audience", "A_legal", "B"]
    parent_revision_id: str | None           # None = the original document
    text_path: str                           # data/runs/<run>/revisions/<rev_id>.md
    sha256: str
    hunks: list[str]
    style_report_id: str | None
    cross_check_report_id: str | None
    gate_status: Literal["pending", "passed", "failed", "escalated"]
```
- A Revision never overwrites anything. Each is a new file + record (R-DATA-01/05).
- `revisions/<rev_id>.diff` is written alongside it (a unified diff) for humans.
- **Unit mapping:** after each revision, units are re-anchored to the new text via hunk
  offsets (`rewrite/anchor.py`). The original unit ids persist with `revision_offsets`.
  New woven text gets new units (origin SYSTEM, with parent = the proposal id).

### 1.2 Style Guide (produced by the Style Analyst, consumed by every rewriter)

> **Updated (29 §7):** the Style Guide is now **generated from the Voice Model** (29). Top
> features become dos; negative features and forbids become don'ts; protected terms and
> signature moves carry over. The voice thresholds in this document (0.85 / 0.88 / 0.70 /
> 0.80) are **base values**, scaled by corpus confidence (29 §3.6).

```python
class StyleGuide(BaseModel):
    version: int
    source_hash: str                         # hash of voice_corpus manifest + VoiceModel version + profile
    voice_summary: str                       # ≤ 150 words
    dos: list[str]                           # e.g. "short punchy sentences after long ones"
    donts: list[str]                         # e.g. "no corporate words: leverage, utilize"
    protected_terms: list[str]               # slang, coined words, names, signature phrases — NEVER "corrected"
    intentional_patterns: list[str]          # fragments, run-ons, lowercase stylings the author uses on purpose
    punctuation_habits: dict[str, str]       # e.g. {"em_dash": "frequent, no spaces"}
    person_and_address: str                  # e.g. "first person; addresses reader as 'you' in lessons"
    rhythm_targets: dict[str, float]         # sentence length mean/stdev from the fingerprint (09 §5)
    examples: list[str]                      # 3–6 short excerpts from the samples (≤ 60 words each)
```
- Built from the Voice Model over `profile/voice_corpus/` (29), the author's accepted text, and the voice fingerprint
  (09 §5).
- The author edits and approves the Style Guide in the TUI **once**, before the first Pass A.
  After that, a new version is proposed only when the samples change.
- `protected_terms` also feeds LanguageTool's ignore list.

### 1.3 Formatting standard (`config/formatting.yaml`)
```yaml
manuscript:
  headings: {chapter: "# Chapter {n}: {title}", section: "## {title}"}
  scene_break: "* * *"
  quotes: curly
  em_dash: "—"             # no spaces (unless the Style Guide says otherwise)
  ellipsis: "…"
  numbers: chicago         # spell out one–one hundred, except statistics & percentages
  percent: "numeral + %"   # "36.2%"
  lists: allowed_in_lessons_only
  max_paragraph_words: 180 # flag, do not force
citations:
  style: chicago_notes     # endnotes per chapter
  endnote_marker: "[^n]"
  bibliography: per_book
```
The Formatter applies the deterministic rules. The Style Guide overrides the manuscript
defaults where they conflict (the author's voice wins), and every override is logged.

## 2. Team members (both passes use these roles)

| Agent | Kind | Does | Never does |
|---|---|---|---|
| **Mechanic** | LanguageTool + LLM adjudicator | Spelling, grammar, and punctuation. LanguageTool proposes; the adjudicator LLM accepts or rejects each suggestion against the Style Guide (e.g. keeps an intentional fragment) | Touch protected terms; rephrase; accept style suggestions ("consider rephrasing") |
| **Formatter** | Deterministic + a small LLM pass for structure | Headings, paragraphing, quotes, dashes, number style, list formatting, endnote markers | Change words (except typographic characters) |
| **Line Editor** (Pass A) / **Master Rewriter** (Pass B) | LLM rewriting agent | Clarity, flow, applying verified corrections, audience and legal edits | Add facts without evidence; remove personal stories; exceed the edit budget; change a stance |
| **Weaver** (Pass B only) | LLM rewriting agent | Writes new passages for accepted proposals, at the chosen placement and in the chosen mode, using the author's answers | Invent personal experiences; write beyond the proposal's word estimate + 25% |
| **Style Analyst** | Measured + LLM | Produces the `StyleReport` for each revision | Edit text |
| **Reference Cross-Checker** | Measured + LLM + internet | Produces the `CrossCheckReport` for each revision | Edit text |

### 2.1 LanguageTool
- Runs as a **local server** (Docker or Java, `settings.yaml → languagetool.url`, default
  `http://localhost:8081`). It is called over HTTP with httpx. No new Python dependency.
- The language is from settings (default `en-US`). `protected_terms` are sent as the
  `ignore` list / a user dictionary.
- If the server is down: F03 circuit → the Mechanic runs LLM-only in **degraded** mode, and
  the report says so.

## 3. Pass A — Mid Polish (Act II)

```
Revision A0 (original text)
  → Mechanic  → hunks (spelling/grammar/punctuation)
  → Formatter → hunks (formatting)
  → Line Editor → hunks (clarity/flow + VERIFIED fact corrections only)
  = Revision A1
  → Style Analyst  → StyleReport       ┐
  → Cross-Checker  → CrossCheckReport  ┘ both in parallel
  → GATE-A
       pass → Act III
       fail → Line Editor receives both reports → A1' (loop ≤ 3)
             still failing → escalate to the author (TUI: "Pass A needs you")
```

### 3.1 Line Editor rules (Pass A)
- It may apply a fact correction **only** when the unit's VerdictRecord has a
  `suggested_correction` and final_verdict ∈ {PARTIALLY_TRUE, MISLEADING, FALSE}. The hunk
  must carry the evidence_ids. If the verdict is UNSUPPORTED/UNVERIFIABLE, it doesn't correct;
  it adds a `[[VERIFY]]` marker comment (not visible in the export) for the author.
- It addresses `flow_breaks` (09 §4) with at most one bridging sentence each, marked origin
  SYSTEM.
- It works paragraph by paragraph with the Style Guide + the neighbouring paragraphs in context.

### 3.2 Gate A (`rewrite/gates.py`)
PASS requires **all** of:
- Style: `voice_similarity(A1, style reference) ≥ 0.85` **and** no hunk with a local
  similarity < 0.70 **and** 100% of protected terms intact.
- Cross-check: `cross_check.pass_rate == 1.0` (every checked item is `match` or
  `correctly_corrected`), and **0** `new_unverified_claim`.
- Meaning preservation (§5.3) passes for 100% of the hunks.
- The edit budget is respected in every paragraph.

## 4. Pass B — Master Rewrite (Act VI)

Inputs: the latest validated revision (after Acts III–IV), the accepted
`IntegrationPlanItem`s (18), the legal required edits (22), the final audience brief (20), and
the Shadow items marked "address in rewrite".

```
Revision B0 (= latest validated revision)
  → Weaver: one woven insert per IntegrationPlanItem (graded G-HUNK-B individually)
  → Master Rewriter: whole-chapter flow pass (transitions around the inserts, audience
    edits, remaining legal edits)
  → Mechanic → Formatter (final proof + endnotes + bibliography)
  = Revision B1
  → Style Analyst ┐
  → Cross-Checker ┘ → GATE-B (stricter, §4.2)
  → Legal Delta Review (22 §7)        — only hunks changed since Act IV
  → Audience final check (20 §5.3)    — no regression on the primary metrics
  → Shadow final grade (10)           — rubric goals
  → Grade every hunk (G-HUNK-B ≥ 95) → Author hunk review (accept/reject each)
  → apply the decisions → Revision B-final → EXPORT (§6)
```

### 4.1 Weaver rules
- Personal content in woven text comes **only** from `author_answers` in the plan item, or
  from existing units. It never invents memories, feelings, or events.
- Facts come only from the plan item's evidence. Every factual sentence gets an endnote.
- For `short_quote_with_citation`: ≤ 300 characters from a verified excerpt, never lyrics
  (07 §2).
- Its length stays within `word_estimate × 1.25`.

### 4.2 Gate B
Everything in Gate A, plus:
- `voice_similarity ≥ 0.88` for the chapter, and ≥ 0.80 for every woven insert.
- Every endnote resolves to Evidence with a URL + access date.
- 0 open `[[VERIFY]]` markers (they must be resolved or explicitly waived by the author).
- The Legal Delta Review is passed, the audience check shows no regression, and the Shadow
  hard goals are met (or waived with a reason).

## 5. Style Analyst and Reference Cross-Checker (the sibling pair)

### 5.1 StyleReport
```python
class StyleReport(BaseModel):
    id: str; revision_id: str
    fingerprint_before: VoiceFingerprint; fingerprint_after: VoiceFingerprint
    voice_similarity: float                  # 09 §5.2 method, against the Style Guide reference
    per_hunk_similarity: dict[str, float]    # hunk_id → local similarity (±2 sentences of context)
    protected_terms_intact: float            # 0–1
    drift_notes: list[str]                   # e.g. "hunk_12 sounds corporate: 'facilitate'"
    tone_shift: dict[str, float]             # warmth/authority/vulnerability deltas (from 20 §3 tonality metrics)
    verdict: Literal["pass", "fail"]
    fix_requests: list[str]                  # concrete, per hunk
```

### 5.2 CrossCheckReport
The Cross-Checker extracts every **checkable item** from the revision (numbers, dates, names,
titles, quotes, case names, study references, media details, endnotes) and matches each one
against the source of truth:

| Item status | Meaning |
|---|---|
| `match` | Identical to the original unit, and the unit's verdict is acceptable |
| `correctly_corrected` | Changed exactly as the VerdictRecord / legal edit / plan item specifies |
| `drifted` | A number, name, or quote changed without authorization → **FAIL** |
| `new_unverified_claim` | A factual statement not traceable to evidence → **FAIL** |
| `lost_attribution` | A citation, "according to…", or "alleged" was removed → **FAIL** |
| `stale_source` | The source is now unreachable or changed (re-fetch + excerpt check) → warning, and a re-fetch is attempted |

- Internet use: re-fetch every source cited in the revision (cache-aware) and re-verify the
  excerpt, catching link rot and silent page edits. It also runs a quick search for
  retractions or corrections for academic/legal items published since the verification date.
- `pass_rate = (match + correctly_corrected) / all_items` must be 1.0 at the gate.

### 5.3 Meaning preservation check (`rewrite/meaning.py`)
For every hunk (except woven inserts):
1. Deterministic: numbers, named entities, and negations ("not", "never", "no") in the
   `before` text must appear in `after`, unless the hunk is an authorized correction.
2. LLM entailment check (task `rewrite.entailment`, temperature 0):
   `{"same_meaning": bool, "stance_changed": bool, "lost_content": [..]}`. Fail if
   `same_meaning` is false or `stance_changed` is true.

## 6. Master output export (`reports/manuscript.py`)
`data/exports/<book>/<date>/`:
- `manuscript.md` + `manuscript.docx` (python-docx, using formatting.yaml styles)
- `endnotes.md`, `bibliography.md` (Chicago), `sources.json` (every Evidence record)
- `change_log.md` (every accepted hunk with its reason and agent)
- `fact_check_appendix.md` (claims, author-facing labels, sources)
- `legal_memos/` (22 §6), with the "not legal advice" banner
- `audit_bundle.json` (gates passed, grades, audience metrics, style/cross-check reports,
  Shadow scores)

## 7. Routing additions
```yaml
  rewrite.mechanic_adjudicate: {provider: local, temperature: 0.0, max_output_tokens: 1500}
  rewrite.format_structure:    {provider: local, temperature: 0.0, max_output_tokens: 1500}
  rewrite.line_edit:           {provider: muse,  temperature: 0.3, max_output_tokens: 3000}
  rewrite.master:              {provider: muse,  temperature: 0.4, max_output_tokens: 6000}
  rewrite.weave:               {provider: muse,  temperature: 0.5, max_output_tokens: 3000}
  rewrite.style_guide:         {provider: muse,  temperature: 0.2, max_output_tokens: 2500}
  rewrite.style_report:        {provider: muse,  temperature: 0.0, max_output_tokens: 2000}
  rewrite.cross_check:         {provider: muse,  temperature: 0.0, max_output_tokens: 3000}
  rewrite.entailment:          {provider: local, temperature: 0.0, max_output_tokens: 300}
```
