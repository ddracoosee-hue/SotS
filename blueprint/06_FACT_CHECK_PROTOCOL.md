# 06 — FACT-CHECK PROTOCOL (Stages 4–5)

This is the heart of SotS. Build it with the most care.

## 1. The two axes every verdict has

The author wants to separate **how true** something is from **what kind of truth** it
rests on. Every checked unit therefore gets two labels:

| Axis | Field | Values |
|---|---|---|
| How true | `final_verdict` | TRUE, MOSTLY_TRUE, PARTIALLY_TRUE, MISLEADING, FALSE, UNSUPPORTED, UNVERIFIABLE |
| What kind of truth | `truth_basis` | PRIMARY_RECORD ("directly true"), ACADEMIC, REFERENCE, JOURNALISM, FACT_CHECK_ORG, SOCIAL_MEDIA ("social media story"), FICTIONAL_MEDIA ("from a movie/TV show"), OPINION_COMMENTARY, AUTHOR_SUPPLEMENT |

Report labels shown to the author (map them exactly):

| Condition | Author-facing label |
|---|---|
| verdict TRUE/MOSTLY_TRUE and basis PRIMARY_RECORD | **Directly true (on the record)** |
| verdict TRUE/MOSTLY_TRUE and basis ACADEMIC | **Academically supported** |
| verdict TRUE/MOSTLY_TRUE and basis JOURNALISM/REFERENCE/FACT_CHECK_ORG | **Reported true** |
| verdict PARTIALLY_TRUE or MISLEADING | **Partially true** (plus what is off) |
| basis SOCIAL_MEDIA only | **Social media story**: "it happened online" is separate from "what it claims is true" |
| basis FICTIONAL_MEDIA | **From fiction (film/TV/book)**: not real-world evidence |
| FALSE | **False** |
| UNSUPPORTED / UNVERIFIABLE | **Could not verify** |
| NOT_CHECKABLE | **Personal / narrative** (not fact-checked, by design) |

## 1A. Third axis: the author's epistemic tier
Every VerdictRecord also gets an `epistemic_tier` (DF / PT / IE / DEBUNKED / HEDGE), computed
by `verify/tiers.py` from the verdict + basis (25 §1–2). Tier mismatches with the author's own
tags are findings (ET-02). Claim kinds SCRIPTURE_QUOTE, SCRIPTURE_TERM, PATRISTIC_ATTRIBUTION,
and EVIDENCE_GRADE follow 25 §4–5. The **Brief Audit** (Act 0, 23 §4) runs this whole protocol
over `profile/anchors.yaml` before any dictation arrives. Its `preflags` are leads, not findings.

## 2. Source tiers (`config/source_tiers.yaml`)

```yaml
# Maps domain patterns to tier (1 = strongest) and source_class.
# First match wins. Unknown domains default to tier 4, OPINION_COMMENTARY.
rules:
  - {pattern: "courtlistener.com",      tier: 1, class: primary_record}
  - {pattern: "*.gov",                  tier: 1, class: primary_record}
  - {pattern: "*.gov.*",                tier: 1, class: primary_record}
  - {pattern: "supremecourt.gov",       tier: 1, class: primary_record}
  - {pattern: "data.worldbank.org",     tier: 1, class: primary_record}
  - {pattern: "who.int",                tier: 1, class: primary_record}
  - {pattern: "doi.org",                tier: 2, class: academic}
  - {pattern: "pubmed.ncbi.nlm.nih.gov",tier: 2, class: academic}
  - {pattern: "ncbi.nlm.nih.gov",       tier: 2, class: academic}
  - {pattern: "*.edu",                  tier: 2, class: academic}
  - {pattern: "openalex.org",           tier: 2, class: academic}
  - {pattern: "pewresearch.org",        tier: 2, class: academic}
  - {pattern: "*.wikipedia.org",        tier: 3, class: reference}
  - {pattern: "britannica.com",         tier: 3, class: reference}
  - {pattern: "apnews.com",             tier: 3, class: journalism}
  - {pattern: "reuters.com",            tier: 3, class: journalism}
  - {pattern: "bbc.co.uk",              tier: 3, class: journalism}
  - {pattern: "npr.org",                tier: 3, class: journalism}
  - {pattern: "snopes.com",             tier: 3, class: fact_check_org}
  - {pattern: "politifact.com",         tier: 3, class: fact_check_org}
  - {pattern: "factcheck.org",          tier: 3, class: fact_check_org}
  - {pattern: "medium.com",             tier: 4, class: opinion_commentary}
  - {pattern: "substack.com",           tier: 4, class: opinion_commentary}
  - {pattern: "tiktok.com",             tier: 5, class: social_media}
  - {pattern: "x.com",                  tier: 5, class: social_media}
  - {pattern: "twitter.com",            tier: 5, class: social_media}
  - {pattern: "instagram.com",          tier: 5, class: social_media}
  - {pattern: "facebook.com",           tier: 5, class: social_media}
  - {pattern: "reddit.com",             tier: 5, class: social_media}
  - {pattern: "youtube.com",            tier: 5, class: social_media}
default: {tier: 4, class: opinion_commentary}
```
The author may edit this file. Wikipedia is tier 3: it is good for finding primary
sources, but a claim resting only on Wikipedia cannot reach TRUE (see VR-GEN-02).

## 3. Stage 4 — RESEARCH (`research/`)

For each unit with `content_type == FACTUAL_CLAIM` (including embedded-claim children):

### 3.1 Plan queries (`planner.py`, task `research.plan_queries`)

```python
class QueryPlan(BaseModel):
    claim: str                         # = unit.normalized_claim
    key_facts_to_confirm: list[str]    # each atomic fact, e.g. "the year", "the percentage", "the outcome"
    queries: list[str]                 # 3–6 web queries, from neutral to adversarial
    structured_lookups: list[StructuredLookup]  # direct API lookups (below)

class StructuredLookup(BaseModel):
    fetcher: Literal["wikipedia", "courtlistener", "openalex", "crossref",
                     "google_factcheck", "tmdb", "openlibrary", "musicbrainz", "supplements"]
    query: str
```

Required query patterns (checked in code; add the missing ones deterministically):
- At least 1 query phrased neutrally (not in the author's words).
- At least 1 query designed to find **contradicting** evidence
  (e.g. `"<claim topic> myth"`, `"<statistic> debunked"`, `"<case> overturned"`).
- For `STATISTIC`: 1 query aimed at the original data publisher.
- For `LEGAL_CASE`: always a `courtlistener` lookup.
- For `ACADEMIC_FINDING`: always an `openalex` lookup; add `crossref` if a DOI is named.
- For `SOCIAL_MEDIA_CASE`: always a `google_factcheck` lookup, plus 1 query containing
  "fact check".
- Always a `supplements` lookup (the author's own reference files).

### 3.2 Fetchers (`research/fetchers/`)

Each fetcher implements:
```python
class Fetcher(Protocol):
    name: str
    async def lookup(self, query: str) -> list[FetchedDoc]: ...
    async def fetch_url(self, url: str) -> FetchedDoc | None: ...

class FetchedDoc(BaseModel):
    url: str; title: str; publisher: str | None; published_date: date | None
    text: str                  # full readable text (trafilatura for HTML)
    content_hash: str
    fetcher: str
```

| Fetcher | Source | Key needed | Notes |
|---|---|---|---|
| `web` | any URL from search hits | no | trafilatura extraction; respect robots.txt; 15 s timeout; skip non-HTML/PDF |
| `wikipedia` | MediaWiki REST API | no | also collect the article's reference URLs as leads for primary sources |
| `courtlistener` | CourtListener API v4 | free token | returns case name, court, date filed, docket, citation, and opinion text |
| `openalex` | OpenAlex API | no (send email in UA) | works, abstracts, DOI, citation count, retraction flag |
| `crossref` | Crossref API | no | DOI metadata, retraction/update notices |
| `google_factcheck` | Google Fact Check Tools API | free key | existing professional fact checks |
| `tmdb` | TMDB API | free key | films/TV: title, year, overview, credits |
| `openlibrary` | Open Library API | no | books: title, author, year, description |
| `musicbrainz` | MusicBrainz API | no (UA required) | songs/albums: artist, date. **No lyric fetching** (copyright) |
| `supplements` | local `supplements/` folder | no | indexed text of the author's files; source_class AUTHOR_SUPPLEMENT |

All fetches are cached in `data/cache/fetch/` by URL hash for `settings.cache.fetch_ttl_days`
(default 30). Fetchers that need a key are **disabled** when the key is missing, and the
report says so.

### 3.3 Candidate selection
- Take the top `settings.research.max_urls_per_unit` (default 8) URLs from the search hits
  and structured lookups, ranked by tier first and search rank second.
- At least 2 must come from different registered domains, when available.
- Fetch them. Drop any document whose text is shorter than 300 characters.

### 3.4 Build evidence (`evidence_builder.py`)
For each fetched document, the researcher (§4) quotes excerpts. The **deterministic**
`citation_check.verify_excerpt(doc.text, excerpt)` then checks each one:
1. Normalize whitespace and quotes in both strings.
2. An exact substring match → score 100.
3. Otherwise rapidfuzz `partial_ratio`. Accept if ≥ 90.
4. Rejected excerpts are logged as `evidence.rejected_excerpt` and never stored (R-TRUTH-02).

## 4. Stage 5 — VERIFY: three-role adversarial process (`verify/`)

The three roles run in sequence for each unit. Each role is a separate LLM call with its
own prompt.

### 4.1 Researcher (`researcher.py`, task `verify.researcher`)
Input: the claim, key_facts_to_confirm, fetched docs (trimmed to their relevant passages
of ≤ 1500 tokens each; see §4.4), claim_kind.
Output:
```python
class ResearcherOut(BaseModel):
    evidence: list[ProposedEvidence]   # url, excerpt (verbatim!), stance, which key_fact it addresses
    fact_status: dict[str, Literal["confirmed", "contradicted", "not_found"]]  # per key fact
    summary: str
    claim_specific: dict               # see §5
```

### 4.2 Skeptic (`skeptic.py`, task `verify.skeptic`)
Input: the claim, the verified evidence (after citation_check), the researcher summary.
The skeptic's job is to attack the researcher's conclusion:
- Are the sources independent, or do they all copy one origin?
- Is the statistic from a different year, place, or population than the author implies?
- Is it a correlation presented as causation?
- Was the court case appealed, overturned, or settled rather than won?
- Is the social media story staged, satire, or debunked?
- Is the study retracted, tiny, unreplicated, or misrepresented?
- Does the evidence support the *exact* claim, or only something nearby?
Output: `SkepticOut(objections: list[str], severity_per_objection: list[Severity], suggested_verdict: Verdict)`

### 4.3 Adjudicator (`adjudicator.py`, task `verify.adjudicator`)
Input: the claim, the evidence, the researcher output, the skeptic output.
Output: `AdjudicatorOut(proposed_verdict, truth_basis, confidence, reasoning, what_is_accurate, what_is_off, suggested_correction)`.
The adjudicator must address every HIGH-severity objection by name in its reasoning. Code
checks this: each HIGH objection's first 40 characters are fuzzy-matched against the
reasoning. If the check fails → retry.

### 4.4 Passage trimming (deterministic)
Before sending a fetched doc to the LLM, split it into paragraphs. Score each paragraph by
keyword overlap with the claim and key facts (BM25-lite: term frequency × inverse document
frequency within the doc). Keep the best paragraphs until 1500 tokens. Keep the order.

## 5. Claim-specific fields (`claim_specific`)

The researcher fills these in, and the rules check them. Missing required fields cap the
verdict.

| claim_kind | Required fields |
|---|---|
| STATISTIC | `value_claimed`, `value_found`, `unit`, `population`, `place`, `year_claimed`, `year_found`, `original_publisher` |
| LEGAL_CASE | `case_name`, `court`, `date_filed`, `docket_or_citation`, `outcome_claimed`, `outcome_found`, `appealed_or_overturned` |
| ACADEMIC_FINDING | `study_title`, `authors`, `year`, `doi`, `sample_size`, `design` (RCT/observational/meta-analysis/other), `retracted`, `finding_claimed`, `finding_found` |
| SOCIAL_MEDIA_CASE | `platform`, `account_or_person`, `approx_date`, `event_occurred` (bool/unknown), `content_true` (bool/unknown), `debunked_by` |
| QUOTE_ATTRIBUTION | `quote_claimed`, `quote_found`, `speaker_claimed`, `speaker_found`, `context` |
| HISTORICAL_EVENT / NEWS_EVENT | `event`, `date_claimed`, `date_found`, `place`, `key_actors` |
| GENERAL_FACT | none |

## 6. Deterministic verdict rules (`verify/rules.py`)

Each rule returns a `RuleCheck`. `final_verdict = min(proposed_verdict, all failed caps)`,
using the strength order in `03 §1`. Each rule is a separate pure function with its own
unit test.

**General**
- **VR-GEN-01** No stored evidence → cap `UNSUPPORTED`.
- **VR-GEN-02** TRUE needs ≥ 2 SUPPORTS evidence from ≥ 2 distinct domains, with at least
  one of tier ≤ 2, and no CONTRADICTS of tier ≤ 2. Otherwise cap `MOSTLY_TRUE`.
- **VR-GEN-03** MOSTLY_TRUE needs ≥ 1 SUPPORTS evidence of tier ≤ 3. Otherwise cap
  `PARTIALLY_TRUE`.
- **VR-GEN-04** Any CONTRADICTS of tier ≤ 2 with no SUPPORTS of equal or better tier →
  cap `MISLEADING`.
- **VR-GEN-05** All evidence tier 5 (social media) → cap `UNVERIFIABLE`, and truth_basis
  = SOCIAL_MEDIA.
- **VR-GEN-06** Evidence whose source_class is FICTIONAL_MEDIA cannot count as SUPPORTS
  for a real-world claim (R-TRUTH-06). Reclassify it to CONTEXT before the other rules run.
- **VR-GEN-07** Verification ran on a fallback local model → cap `MOSTLY_TRUE` (04 §3).

**Statistics**
- **VR-STAT-01** TRUE requires a PRIMARY_RECORD or ACADEMIC source containing `value_found`.
- **VR-STAT-02** |value_claimed − value_found| / value_found > 10% → cap `PARTIALLY_TRUE`.
  > 50% → cap `MISLEADING`.
- **VR-STAT-03** A population or place mismatch → cap `MISLEADING`.
- **VR-STAT-04** |year_claimed − year_found| > 5 when the claim implies "now" → cap
  `PARTIALLY_TRUE`, and the note says "outdated figure".

**Legal cases**
- **VR-LAW-01** Any of case_name, court, or date_filed missing → cap `UNSUPPORTED`.
- **VR-LAW-02** outcome_claimed ≠ outcome_found → cap `FALSE` if they are opposite
  (won/lost), otherwise `MISLEADING`.
- **VR-LAW-03** appealed_or_overturned is true and the author did not mention it → cap
  `MISLEADING`.

**Academic**
- **VR-ACA-01** retracted == true → cap `FALSE`, and the note says "retracted study".
- **VR-ACA-02** design is observational and the author states causation → cap `MISLEADING`.
- **VR-ACA-03** No DOI and no OpenAlex match → cap `PARTIALLY_TRUE`.

**Social media**
- **VR-SOC-01** Split the verdict: `event_occurred` answers "did the post/event happen", and
  `content_true` answers "is what it claims true". The final verdict is about the author's
  sentence. If the author presents the content as fact and content_true is not true → cap
  `MISLEADING`.
- **VR-SOC-02** debunked_by is non-empty → cap `FALSE` for claims that present the content
  as fact.

**Quotes**
- **VR-QUO-01** Quote fuzzy score < 85 against quote_found → cap `PARTIALLY_TRUE`.
- **VR-QUO-02** speaker_found ≠ speaker_claimed → cap `FALSE` (misattribution).

## 7. Confidence (deterministic formula, not the LLM's number)

```
confidence = clamp(0, 1,
    0.35 * tier_score          # best supporting tier: 1→1.0, 2→0.85, 3→0.6, 4→0.3, 5→0.1
  + 0.25 * independence        # min(1, distinct_supporting_domains / 3)
  + 0.20 * fact_coverage       # confirmed key facts / total key facts
  + 0.10 * rules_passed_ratio
  + 0.10 * (1 - high_objections_unresolved_ratio)
)
```
Store the LLM's own confidence in the `claim_specific.llm_confidence` field, for eval only.

## 8. Output per unit

One `VerdictRecord`, plus `Evidence` rows. The Markdown report section for each unit shows:
the author's exact words → author-facing label → what's accurate → what's off → sources
(title, publisher, date, link, excerpt) → skeptic's strongest objection → the suggested
neutral correction.

## 9. The Fact-Check Team (expanded roster)

Stages 4–5 are carried out by a **team** of agents built on the shared runtime (16). The
three-role process in §4 stays the core. Specialists and scouts surround it.

| Agent | Card | Job | Internet |
|---|---|---|---|
| **Triage Lead** | `fact_check/triage.yaml` | Orders units by importance (message priority × claim centrality × risk), assigns specialists, sets per-unit budgets | no |
| **Statistics Specialist** | `fact_check/stats.yaml` | Finds the original data publisher, pulls the actual table (`parse_table`), recomputes the figure (`compute`), and checks year/population/place | yes |
| **Court Records Specialist** | `fact_check/courts.yaml` | CourtListener docket + opinion retrieval, the procedural history (appeals, reversals, settlements) | yes |
| **Academic Specialist** | `fact_check/academic.yaml` | OpenAlex/Crossref, retraction checks, study design + sample size, replication status | yes |
| **Social Media Forensics** | `fact_check/social.yaml` | Establishes whether a viral event happened (dates, archived copies via search, fact-check orgs), separates `event_occurred` from `content_true` | yes |
| **Quote & Attribution Specialist** | `fact_check/quotes.yaml` | Traces quotes to their earliest verifiable source; flags misattributions (common for "internet quotes") | yes |
| **Researcher / Skeptic / Adjudicator** | §4 | The core verification of every unit, fed by the specialists' evidence | yes / no / no |
| **Discovery Scout** | `fact_check/discovery_scout.yaml` | Collects **adjacent finds** during research (a stronger source, a better case study, a more current statistic, a striking counterpoint) and turns the best into Proposals (18) | yes |
| **Media Scout** | `fact_check/media_scout.yaml` | Works with Stage 6 (07). Finds films, books, series, songs, podcasts, and artworks that **echo or contrast** the author's themes, and pitches them as `media_echo` / `media_contrast` / `media_context` proposals with targeted questions (18 §3) | yes |

### 9.1 Specialist → core handoff
Specialists return `SpecialistFindings` (their Evidence ids + the filled `claim_specific` fields),
which are passed to the Researcher as pre-verified material. The Researcher may add evidence but
may not discard specialist evidence without saying why (the Skeptic sees both).

### 9.2 Discovery capture (during research, no extra searches)
While any fact-check agent reads fetched documents, it may emit `DiscoveryNote`s:
```python
class DiscoveryNote(BaseModel):
    id: str; unit_id: str; agent: str
    kind: Literal["stronger_source", "better_example", "newer_data", "counterpoint",
                  "related_case", "related_study", "media_mention"]
    summary: str; evidence_id: str        # must be verified
    why_interesting: str
```
Limit: ≤ 3 per unit. They are stored, deduplicated, and handed to the scouts.

### 9.3 Scouting (Act V)
1. The **Discovery Scout** ranks the DiscoveryNotes by (relevance to the chapter messages ×
   novelty × source tier). For the top N (`discovery.max_candidates_per_chapter`, default 10),
   it may do up to 3 additional searches to strengthen the case, then drafts a Proposal.
2. The **Media Scout** runs per chapter:
   - Inputs: the chapter's themes (08), core messages (09), the concept graph hubs (11),
     media the author already cites (07), and `media_mention` notes.
   - It searches for works by theme (`"<theme>" film OR novel OR memoir`, curated lists,
     critical essays), resolves each candidate via 07 §1, and gathers established readings
     (07 §2).
   - Hard filters: the work is resolved (identity verified); the reading is sourced; it is
     **not already cited** by the author; it is not a work the author excluded
     (`profile/book.md → media_exclusions`).
   - It drafts `media_echo` / `media_contrast` proposals with the required question patterns
     (18 §3).
3. All drafts go to the Quality Gate (G-PROP ≥ 95). Passed proposals are queued on the
   Proposal Desk.

### 9.4 Fact-check team goals (add to `system_goals.yaml`)
```yaml
fact_check_team:
  specialist_coverage:     {target: "==1.0", how: "every STATISTIC/LEGAL/ACADEMIC/SOCIAL/QUOTE unit got its specialist"}
  recomputed_stat_share:   {target: ">=0.8", how: "statistics recomputed from a parsed primary table"}
  discovery_yield:         {target: "track", how: "proposals passing G-PROP per chapter"}
  media_proposal_accept:   {target: "track", how: "author accept rate for media_* proposals"}
