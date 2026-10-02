# 25 — THE AUTHOR'S EPISTEMIC STANDARD, EVIDENCE GRADES, AND SCRIPTURE

The briefs define the author's own truth-labelling system. SotS adopts it as a **third axis**
alongside `final_verdict` (how true) and `truth_basis` (what kind of source) (06 §1).

## 1. The tiers

| Tier | Tag | Meaning | Assigned when |
|---|---|---|---|
| DF | **[Documented Fact]** | data, citations, records | the claim is verified TRUE/MOSTLY_TRUE with basis PRIMARY_RECORD / ACADEMIC / REFERENCE / JOURNALISM |
| PT | **[Primary Theory]** | validated models and frameworks (SDT, attachment, Lewis/Tangney…) | the claim presents a named theory/model accurately (verified attribution + description) |
| IE | **[Interpretive Extension]** | the author's synthesis, application, or meaning-making | any application of a theory beyond its evidence, metaphors, faith applications, readings of media |
| — | **Debunked / Withdrawn: Do Not Cite** | retracted or discredited | VR-ACA-01 retracted, or a formal withdrawal/correction found |
| — | **Replication Failures: Hedge** | contested by failed replications | a documented replication failure or a meta-analysis showing weak/no effect |

New enum `EpistemicTier {DF, PT, IE, DEBUNKED, HEDGE}` and a field on VerdictRecord:
`epistemic_tier: EpistemicTier | None` + `tier_claimed_by_author: EpistemicTier | None`.

## 2. Tier rules (deterministic, `verify/tiers.py`)
- **ET-01** Tier is computed from the verification, never taken from the LLM or the author's label.
- **ET-02** If the author tagged a claim (in dictation or the brief) and the computed tier
  differs, that is a **Tier Mismatch** finding (e.g. the author wrote [Documented Fact] but the
  claim is PARTIALLY_TRUE → propose PT/IE or a corrected figure). Shown in the claims report and
  sent to the Shadow as a `fact_risk`.
- **ET-03** Any claim whose evidence includes a retraction → DEBUNKED; the draft must not cite
  it as support (the Cross-Checker fails any support use).
- **ET-04** A claim with a documented replication failure → HEDGE; the draft must use hedged
  language (a list of approved hedges in config), which the Cross-Checker verifies.
- **ET-05** Faith statements → no tier (NOT_CHECKABLE belief); scripture quotations/terms get
  their own checks (§3).

## 3. Display (author decision 2026-09-28: "inline only where it matters")
- **Inline style (updated 2026-09-28 from the author-final Ch1):** `formatting.yaml → epistemic.inline_style`
  defaults to **`prose`**. Science/statistics claims carry the tier as a prose signal in the
  author's manner. DF = study + year + sample/design caveat; PT = named thinker + framework;
  IE = "my inference rather than their finding"; HEDGE = the replication story; BELIEF =
  "what follows is my personal opinion". The Cross-Checker verifies that each prose signal
  matches the computed tier. **Bracket style** (below) is optional (`inline_style: bracket`).
- **Bracket tags** (when enabled) appear in the prose only on **science and statistics claims** (claim_kind ∈
  {STATISTIC, ACADEMIC_FINDING} or anchor type ∈ {research, statistic}). Format:
  `…raised pain thresholds by roughly 10% [Documented Fact].`
- Everything else gets its tier in the endnote (`[^12]: [Primary Theory] Nathanson, *Shame and
  Pride* (1992)…`) and in the fact-check appendix.
- DEBUNKED items are never cited as support. If the author discusses them (as Ch10 does with the
  positivity ratio), the inline tag reads `[Withdrawn: shown here as a cautionary example]`.
- A reader's key explaining the tags appears before the first inline tag (the
  book_architecture recommendation: a reader's note or Ch1).
- The Formatter implements this (`formatting.yaml → epistemic.inline_kinds`), and the
  Cross-Checker verifies that every inline tag equals the computed tier.

## 4. Protocol evidence grades (new claim kind `EVIDENCE_GRADE`)
Every protocol in the briefs claims a grade ("Strong", "Moderate-Strong", "Moderate",
"Practical"). The **Evidence-Grade Auditor** (Fact-Check Team) verifies each one:

| Grade | Requires |
|---|---|
| **Strong** | ≥ 1 meta-analysis or ≥ 2 RCTs supporting *this kind of intervention* for *this outcome* in adults |
| **Moderate** | RCTs or strong longitudinal evidence for the mechanism, with the intervention itself less tested |
| **Emerging** | small, preliminary, or indirect studies |
| **Practical** | experience-based / the author's practice; no empirical claim |
| **Faith-based** | rationale from scripture or theology (valid for readers of faith; not an evidence grade) |

Rules:
- **EG-01** Theory strength does not equal intervention strength (e.g. Lewis/Tangney theory is
  strong, but the "grammar audit" intervention is at most Moderate).
- **EG-02** Scripture and theology cannot support an empirical grade. A protocol citing both is
  split: `Evidence: Moderate (recovery science) · Faith basis: Heschel, Brueggemann`.
- **EG-03** Celebrity anecdotes are illustrations, never evidence ("Shrink the Audience
  [Moderate — Cole]" → Practical).
- **EG-04** A grade mismatch becomes a Proposal (G-PROP) with the verified grade and sources;
  the author decides the final wording.

## 5. Scripture and theology (author decision: check quotes + terms, respect faith)

New claim kinds: `SCRIPTURE_QUOTE`, `SCRIPTURE_TERM` (Greek/Hebrew meaning), and
`PATRISTIC_ATTRIBUTION`.

| What | Checked how | Verdict style |
|---|---|---|
| **Verse text and reference** (e.g. Mt 11:28–30, Mark 10:35–45) | Compared with the **NASB** (the author's decision, 2026-09-28: the NASB is the main translation for fact-checking and quote gathering; edition: **NASB 2020**, see §5.1) via a licensed/public NASB text source; reference ↔ text match. Quotes in the manuscript are gathered from the NASB unless the author explicitly marks another translation (`[KJV]` etc.) | TRUE / MISQUOTED / WRONG_REFERENCE |
| **Original-language terms** (chrēstos, tektōn, ek psychēs, ophthalmodoulia, sympaschei, nēpsis) | Lexicon sources (public lexicon entries, e.g. Strong's/Thayer via public sites; scholarly articles); transliteration check | SUPPORTED / CONTESTED GLOSS / UNSUPPORTED GLOSS |
| **Patristic attributions** (Klimakos's stages of temptation) | Translation of the primary text + scholarly secondary sources | as QUOTE_ATTRIBUTION |
| **Interpretations** ("the easy yoke is well-fitting", "Paul subverts ancient fables") | Rated like media readings (07 §3): `supported_reading` / `contested_reading` / `plausible_personal_reading` / `contradicted_by_source` | never "false"; the framing is advised |
| **Faith claims** ("your worth is a received gift", "the soul is the breath of life") | **Not checked**: NOT_CHECKABLE belief | — |

Rules:
- **SC-01** No agent argues for or against the faith itself. The Skeptic role in verification
  may challenge an *exegetical claim*, never the belief.
- **SC-02** Audience panels include personas of faith and of no faith. Faith passages are
  measured for **reactance** (preachiness), not agreement. Readers who don't share the faith
  should still feel invited rather than recruited (book_architecture recommendation: faith
  prompts are offered as options).
- **SC-03** Legal counsel L3/L8 review the NASB quotation permission terms from The Lockman
  Foundation (the quotation limits and the required copyright notice for the edition used). The
  system tracks the total NASB verses quoted, and the notice goes on the copyright page. The
  exact terms must be fetched and verified, not assumed.

### 5.1 Translation choice per quote (OI-34 resolved: NASB 2020)
- The default for checks and quote gathering is **NASB 2020**. The author's rule is
  "whatever is better for the audience to connect", and the 2020 revision's contemporary
  English suits adult Gen Z and Millennial readers.
- A detector compares each quote with the NASB 2020, NASB 1995 and KJV wording for the same
  reference. If the author's text follows another translation, the Scripture Specialist raises
  a Proposal with two options:
  - (a) switch to the NASB 2020 wording, or
  - (b) keep the familiar wording with an explicit label, e.g. "(KJV)".

  The author chooses per quote.
- On request, the Audience Lab can compare how readers connect with each wording of a key
  verse. The result is advisory only.
- Known Ch1 cases to check:
  - Matthew 15:14, "If the blind lead the blind, both shall fall into the ditch", which reads as KJV-style wording
  - 1 Thessalonians 5:23, "spirit and soul and body"

## 6. Composite and hypothetical cases
New content label `COMPOSITE_CASE` (e.g. Ch9's "24-year-old digital marketer"). It must be
disclosed in the text or a note ("a composite drawn from…"). The Cross-Checker fails any
composite presented as a real, identifiable person. Legal L8 checks the disclosure.

## 7. Author-declared provenance markers (author directive, 2026-09-28)

"When I specify information came from a live source, or something is my personal belief, make
sure to structure the information as such in the regenerated process to the final output."

### 7.1 Markers the author can use in dictation
| Marker (any of) | Meaning | What the system does |
|---|---|---|
| `[LIVE: <source>]`, `[SOURCE: <source>]`, "I saw this on…", "according to…" | Information from a **live/external source** (article, video, podcast, post, broadcast, talk, interview) | The Fact-Check Team fetches and verifies the named source (R-TRUTH-02). If it can't be fetched (e.g. an in-person talk) → `author_attested_source` with the author's description, labelled as such |
| `[BELIEF]`, `[I BELIEVE]`, "I believe…", "my conviction is…" | **Personal belief** | NOT_CHECKABLE; never converted into fact phrasing |
| `[EXPERIENCE]`, `[MEMORY]` | Personal experience | NOT_CHECKABLE for truth; protected by R-SYN-01 |
| `[OPINION]` | The author's opinion/assessment (incl. about public figures) | NOT_CHECKABLE for truth, but any embedded facts are verified; legal defense basis "opinion" |
| `[SPIRAL]` (routing marker, not provenance; combine with the others) | Material meant for the **provocation-spiral serial** (OI-36, open to additions) | Tags the unit `serial: provocation_spiral`; Block Synthesis routes it to the right beat (ch03 / ch04 / ch12), and it is logged in `profile/provocation_spiral_analysis.md` §7 |

The markers are detected in ingest (T04A.034). Natural-language cues ("I believe") are detected
by the classifier with a confidence score; low confidence → review queue.

### 7.2 Carrying provenance to the final output (R-PROV)
- **R-PROV-01** Units carry `author_provenance: live_source | belief | experience | opinion | None`
  and `source_ref` (for live sources).
- **R-PROV-02 Belief stays belief.** Synthesis and rewrites must keep first-person belief
  framing ("I believe…", "My conviction is…", "As I see it…"). The Cross-Checker fails any hunk
  that turns a `[BELIEF]` unit into an unqualified factual assertion (T-FRAME in the Master Audit).
- **R-PROV-03 Live sources are attributed.** The final text names the source in the prose where
  it matters ("As <outlet/creator> reported in <month year>…") **and** in an endnote with the
  URL + access date. Verified → the normal tier; unverifiable → the endnote says "author-attested
  source; not independently verified", and the prose uses "I came across…" framing.
- **R-PROV-04 Opinions about public figures stay opinions.** For named people (e.g. the Ch4
  influencers), factual statements must be verified with sources. Evaluations are phrased as the
  author's opinion and grounded in the cited, verified conduct. Never diagnoses (R-PSY-02).
- **R-PROV-05** The fact-check appendix lists every unit by provenance class, so the reader can
  see what is sourced, what is belief, and what is experience.
