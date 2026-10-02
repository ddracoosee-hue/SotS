# P07 — Research Tools (search, fetchers, tiers, citation check)

**Prerequisites:** P06. **Blueprint refs:** 06 §2–§3, 04 §7, 16 §3.

## Search providers
- [ ] **T07.001** | `research/search/base.py` | The SearchProvider protocol + a chain runner (tries the providers in order, merges and dedupes by URL, keeping the best rank). | Test.
- [ ] **T07.002** | `research/search/searxng.py` | The SearXNG JSON API client (`/search?format=json`). | respx test.
- [ ] **T07.003** | `research/search/tavily.py` | The Tavily API client (key from .env; disabled without a key). | respx test.
- [ ] **T07.004** | `research/search/muse_search.py` | A stub that activates only if `providers.muse.supports_web_search` (OI-03). | Test: disabled by default.

## Fetchers (each: lookup + fetch_url, cache, politeness, F02/F03/F13/F14/F15)
- [ ] **T07.010** | `fetchers/web.py` | httpx GET → content-type check → trafilatura extraction (HTML) or pypdf (PDF) → FetchedDoc; stores the full text in `data/cache/fetch/<hash>.txt`; TTL. | respx tests: HTML, PDF, 404, non-text, oversized.
- [ ] **T07.011** | `fetchers/wikipedia.py` | REST summary + the full-article HTML sections; extracts the reference URLs as leads; section extraction by heading name (for Plot/Themes/Reception). | respx tests.
- [ ] **T07.012** | `fetchers/courtlistener.py` | Search API v4 (case name, court, date filed, docket number, citation), opinion text retrieval, docket entries for the procedural history. Token header. | respx tests with 2 fixtures.
- [ ] **T07.013** | `fetchers/openalex.py` | Works search; the abstract (inverted-index reconstruction); DOI; cited_by_count; `is_retracted`; the mailto in the UA. | respx tests; an abstract-reconstruction unit test.
- [ ] **T07.014** | `fetchers/crossref.py` | DOI metadata; `update-to`/retraction notices. | respx test.
- [ ] **T07.015** | `fetchers/google_factcheck.py` | Claim Search API → claimReview items (publisher, rating, URL). | respx test.
- [ ] **T07.016** | `fetchers/tmdb.py` | Search movie/TV → details, credits, overview. | respx test.
- [ ] **T07.017** | `fetchers/openlibrary.py` | Search → work → description, authors, first publish year. | respx test.
- [ ] **T07.018** | `fetchers/musicbrainz.py` | Recording/release search (UA required, 1 rps). **No lyrics.** | respx test; a test asserting no lyric endpoints exist.
- [ ] **T07.019** | `fetchers/supplements.py` | Searches the indexed supplements (BM25-lite) → FetchedDoc with source_class AUTHOR_SUPPLEMENT. | Test.
- [ ] **T07.020** | `fetchers/registry.py` | Enables/disables fetchers by key presence; `status()` lists them for the CLI/doctor. | Test.

## Tiers + citation check + evidence
- [ ] **T07.030** | `research/tiers.py` | Domain pattern matching (fnmatch on the registered domain + subdomains; first match wins; default). | Tests: 15 URLs → the expected tier/class.
- [ ] **T07.031** | `verify/citation_check.py` | `verify_excerpt(doc_text, excerpt) -> (ok, score)`: normalize whitespace/quotes/dashes, exact → 100, else partial_ratio ≥ 90. | Tests: exact; curly vs straight quotes; line-wrapped; an invented sentence → fail; a too-short excerpt (< 20 chars) → fail.
- [ ] **T07.032** | `research/passages.py` | BM25-lite paragraph scoring + trimming to 1500 tokens, in order (06 §4.4). | Test: the most relevant paragraph is kept.
- [ ] **T07.033** | `research/planner.py` + prompt | QueryPlan generation + the deterministic enforcement of the required patterns per claim_kind (06 §3.1). | Tests: each claim_kind gets its mandatory lookups + a counter query even if the LLM omits them.
- [ ] **T07.034** | `research/candidates.py` | Candidate URL selection: tier-first ranking, domain diversity ≥ 2, the max_urls cap. | Test.
- [ ] **T07.035** | `research/evidence_builder.py` | ProposedEvidence → verify → an Evidence record, or a rejection log (`evidence.rejected_excerpt`). | Test.
- [ ] **T07.036** | `agents/tools/*` | Wire the real fetchers into the P03 tool placeholders (structured lookups, fetch_url, excerpt_verify). | The tool tests now hit the real implementations with respx.
- [ ] **T07.037** | `failsafes/f20_invariants.py` | Register `citation_validity`: every Evidence excerpt is present in its cached page text. | Test with a planted bad excerpt.
- [ ] **T07.090** | — | All green; BUILD_LOG line. | Done.
