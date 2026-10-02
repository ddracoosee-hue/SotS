# 22 — LEGAL CHAMBER (eight counsel, one cohesive defense)

**Purpose:** review everything in the validated revised text for legal exposure and
accuracy of claims about real people, organizations, cases, health, and media. The Chamber
advances **only** when it can produce a **cohesive, evidence-backed argument that explains
and defends the position the text takes**, or has changed the text until it can.

> **R-LEGAL-00 (banner rule):** SotS's legal output is **risk analysis, not legal advice.**
> Every legal report, memo, and TUI screen starts with:
> *"This is automated risk analysis, not legal advice. Have a licensed attorney in your
> publishing jurisdiction review the manuscript before publication."*
> Items the Chamber cannot resolve are marked **"Needs licensed attorney"**, never guessed.

---

## 1. Placement: early, but after the text is regenerated and validated
- **Act IV (main session):** runs on the revision that has passed Gate A (19 §3.2) and the
  Audience loop (20 §5.3). The text is then stable enough that legal work won't be wasted,
  and early enough that legal edits shape the master rewrite.
- **Act VI (Legal Delta Review, §7):** re-reviews only what changed in Pass B (woven
  proposals, rewritten passages).
- **Pre-screen** (cheap, §2): runs on every proposal before grading (criterion U7), and on
  Act I units, so risks are flagged early.

## 2. Intake and pre-screen (`legal/intake.py`)
Deterministic + LLM (task `legal.screen`, local model). It flags units that contain:
- identifiable real people (named, or described identifiably: job + place + event), with
  private vs public figure status (LLM + web check for public-figure evidence)
- allegations of crimes, misconduct, abuse, dishonesty, disease, or sexual conduct
- court cases, arrests, or investigations; sealed/juvenile/expunged indicators
- health, mental-health, medical, legal, or financial advice or claims
- quotes, lyrics, excerpts, images/screenshots descriptions, trademarks/brand names
- private information: addresses, medical details of others, messages/texts, recordings
- the author's employers, contracts, NDAs (asked via an author question if suspected)
- statements about third parties who are minors (e.g. the author's relatives): privacy only.
  The *audience* remains adults.

Output: `LegalIssue`s, each with issue types, unit ids, a preliminary risk (LOW/MED/HIGH), and
the counsel it is assigned to.

## 3. The eight counsel

Each counsel is an agent card (`config/agents/legal/*.yaml`) with a **specialty**, a
**stance tendency**, and a **reasoning method**, deliberately mixed so the perspectives
differ.

| # | Counsel | Specialty | Stance tendency | Method |
|---|---|---|---|---|
| L1 | **Defamation & False Light Counsel** | Defamation, false light, substantial truth, fact vs opinion, public vs private figures, "of and concerning" | Risk-averse (reads as the plaintiff's lawyer would) | Doctrinal: elements test per statement |
| L2 | **Privacy & Consent Counsel** | Public disclosure of private facts, intrusion, identifiability, consent, anonymization techniques, privacy of third parties (incl. relatives) | Risk-averse | Harm-based: "who could be hurt, and how identifiable are they?" |
| L3 | **Copyright, Fair Use & Trademark Counsel** | Quotes, lyrics, excerpts, paraphrase, the four fair-use factors, trademarks in text, titles | Balanced | Factor analysis + publisher permission practice |
| L4 | **Free Expression & Opinion Defense Counsel** | Opinion protection, rhetorical hyperbole, memoir and truth-telling traditions, the public interest | **Expression-maximizing** (defends the author's right to say it) | Precedent from successful defenses |
| L5 | **Court Records & Allegations Counsel** | Accurately describing cases, "alleged", presumption of innocence, fair report privilege, sealed/expunged records | Balanced | Record-matching: text vs the actual docket (uses 06 VR-LAW results) |
| L6 | **Health Claims & Consumer Protection Counsel** | Self-help/mental-health advice liability, disclaimers, unsupported health claims, endorsements/affiliate disclosure guidance | Risk-averse | Regulatory guidance + reader-harm analysis |
| L7 | **International & Jurisdiction Counsel** | Where the book is published/sold: UK/Commonwealth defamation standards, EU/UK data protection, Canada/Australia differences | Comparative / skeptical of US-only reasoning | Comparative law |
| L8 | **Publishing Standards & Ethics Counsel** | Publisher legal-review norms, fact-check expectations, errors & omissions insurance considerations, ethical harm to vulnerable third parties, reputational risk | Pragmatic | "What would a careful publisher require?" |

Supporting roles (not voters):
- **Chamber Clerk** (deterministic, `legal/clerk.py`): assigns issues, runs the rounds,
  enforces the limits, tallies endorsements.
- **Presiding Synthesizer** (LLM, `legal/synthesizer.py`): drafts the cohesive
  Position & Defense Memo from the winning arguments. It has no vote.

Default jurisdiction: `settings.yaml → legal.primary_jurisdiction` (default "US", pending
OI-18), plus `legal.secondary_jurisdictions` (default ["UK", "CA", "AU", "EU"]) for L7.

## 4. Deliberation protocol (per issue, run by the Clerk)

```
R0  Assignment    : each issue → its primary counsel(s) by type + L4 (always) + L8 (always)
R1  Blind review  : each assigned counsel researches independently (internet enabled) and writes an IssueMemo
R2  Position round: all 8 counsel read the R1 memos (not each other's drafts in progress) and file a Position
R3  Cross-exam    : each counsel must REBUT or CONCEDE the two positions most opposed to theirs, with reasons + authorities
R4  Scoring       : the Quality Gate scores every Position's argument (rubric legal_argument, §5)
R5  Synthesis     : the Presiding Synthesizer builds the Position & Defense Memo from the top-scored arguments
R6  Endorsement   : all 8 vote: endorse | endorse_with_reservations | dissent (with reason)
EXIT when: endorse + endorse_with_reservations ≥ 6 of 8
       AND 0 unresolved HIGH risks
       AND memo grade (G-LEGAL) ≥ 95
ELSE → R7 Revision: required text edits are proposed → the Line Editor applies them (legal_edit hunks)
       → Cross-Checker → back to R2 with the edited text (max 3 cycles)
STILL NO EXIT → ESCALATE: the item is BLOCKED; the author sees the two strongest opposing positions,
       options (cut / anonymize / reframe as opinion / get consent / consult attorney), and a
       "Needs licensed attorney" flag. The chapter cannot enter Act VI until the item is
       resolved or the author records an attorney-confirmed waiver.
```

### 4.1 "The best perspectives win"
Arguments are weighted by **quality**, not by headcount:
- The Synthesizer must build the memo from the **highest-scored arguments** (R4), and must
  explain in the memo why lower-scored opposing arguments are outweighed.
- A dissent whose argument scored in the top 2 **must** be answered point by point in the
  memo, or the memo fails its hard check.
- A counsel may not simply defer ("I agree with L4"). Positions without their own reasoning +
  authority are rejected by the validator.

### 4.2 Research tools (internet)
Counsel may use: `web_search`, `fetch_url`, `parse_html`, `parse_pdf`, `courtlistener`,
plus official sources (government statute/code sites, regulator guidance pages, the U.S.
Copyright Office's Fair Use Index, legislation.gov.uk, etc.), all subject to R-TRUTH-02. An
authority is cited only if it was fetched and the excerpt verified. **Invented case law is
the worst failure this Chamber can commit.** It is a release blocker (system goal
`legal_fabricated_authority_rate == 0`).

## 5. Data models (`src/sots/models/legal.py`)

```python
class LegalIssue(BaseModel):
    id: str; run_id: str; revision_id: str
    unit_ids: list[str]
    issue_types: list[Literal["defamation", "false_light", "privacy", "consent", "copyright",
                              "trademark", "court_record", "health_claim", "consumer_protection",
                              "jurisdiction", "ethics", "contract_nda", "other"]]
    persons_involved: list[dict]      # {name_or_descriptor, public_figure: bool|unknown, identifiable: bool}
    preliminary_risk: Severity
    assigned_counsel: list[str]
    status: Literal["open", "in_deliberation", "resolved", "edited", "blocked", "waived"]

class Authority(BaseModel):
    kind: Literal["statute", "case", "regulation", "agency_guidance", "treatise_or_article", "publisher_standard"]
    citation: str; jurisdiction: str
    evidence_id: str                  # fetched + excerpt-verified (R-TRUTH-02)

class Position(BaseModel):
    id: str; issue_id: str; counsel: str; round: int
    stance: Literal["safe_as_is", "safe_with_edits", "risky_needs_major_change", "cut", "needs_attorney"]
    risk: Severity
    argument: str                     # ≤ 400 words
    authorities: list[Authority]
    proposed_edits: list[dict]        # {unit_id, direction: "add 'alleged'", "anonymize", "reframe as opinion", …}
    rebuttals: list[dict]             # {position_id, rebut|concede, reason}
    argument_score: float | None      # from R4

class DefenseMemo(BaseModel):         # the "cohesive argument"
    id: str; issue_id: str
    text_position: str                # what the text claims/implies, neutrally stated
    defense_basis: list[Literal["truth_substantial_truth", "opinion", "fair_report",
                                "public_interest", "consent", "fair_use", "de_minimis",
                                "anonymization", "disclaimer", "not_of_and_concerning"]]
    argument: str                     # the cohesive defense, ≤ 700 words
    required_edits: list[dict]
    residual_risk: Severity
    answered_dissents: list[dict]     # {position_id, answer}
    endorsements: dict[str, Literal["endorse", "endorse_with_reservations", "dissent"]]
    grade_id: str
    needs_licensed_attorney: bool
```

Grader rubric `legal_argument` (for R4 positions; in `config/grader.yaml`): authority quality
(.30, measured), relevance to the exact wording (.25, judged), logical soundness (.20, judged),
practicality of the edits (.15, judged), engagement with the opposing view (.10, judged).
Position scores rank arguments. The 95 gate applies to the **memo** (`legal_memo`, 17 §3.4),
not to individual positions.

## 6. Outputs
- `data/runs/<run>/legal/issues.md`: each issue, its status, and its memo
- `legal_memos/<issue_id>.md`: in the final export (19 §6)
- A TUI "Legal Chamber" screen: issue list with status, the memo, endorsements, dissents, and
  an optional transcript view of the rounds
- Required edits → `legal_edit` hunks (19 §1.1), always cross-checked

## 7. Legal Delta Review (Act VI)
- Scope: only the hunks in Pass B that are woven inserts, or that changed a unit linked to a
  LegalIssue, or that new pre-screen flags touch.
- Panel: the counsel relevant to the issue types + L4 + L8 (minimum 3).
- Exit: ≥ 2/3 endorse + memo ≥ 95 + no HIGH. Otherwise the same escalation as §4.
- Previously resolved memos are re-validated: if an edit touched their units, the memo's
  `text_position` must still hold (entailment check). Otherwise the issue re-opens.

## 8. Routing additions
```yaml
  legal.screen:       {provider: local, temperature: 0.0, max_output_tokens: 1500}
  legal.counsel:      {provider: muse,  temperature: 0.3, max_output_tokens: 3000}   # all 8 (card-specific prompts)
  legal.synthesize:   {provider: muse,  temperature: 0.1, max_output_tokens: 4000}
  legal.entailment:   {provider: local, temperature: 0.0, max_output_tokens: 300}
```
Each counsel has its own prompt file `prompts/legal/L1_defamation.v1.md` … `L8_publishing.v1.md`,
containing its specialty, stance tendency, method, a checklist, and the banner rule.

## 9. Pre-opened issues from the Book Foundation (23 §3.1)
At Act 0, the Clerk opens LegalIssues for every anchor with a `legal:` note in
`profile/anchors.yaml`. Known at foundation time:

| Anchor | Issue types | Preliminary risk | Primary counsel |
|---|---|---|---|
| ch04.A11: named influencers (Sneako, RiceGum, Vlog Squad) "normalize mental illness". **Author decision 2026-09-28: KEEP the names**, with every factual statement cross-checked and verified, and evaluations framed as opinion (R-PROV-04). The Chamber's job is to make the kept version defensible, not to remove it. | defamation, false_light, ethics | **HIGH** | L1, L2, L4, L8 |
| ch04.A03: "celebrities… acting out untreated childhood trauma" | defamation (if applied to named people), ethics | MEDIUM | L1, L8 |
| ch01.A08: manipulation of family, friends, teachers | privacy, consent | MEDIUM | L2 |
| ch05.A02: the best friend's mental-health struggles | privacy, consent | MEDIUM | L2 |
| ch03.A09: coffee-shop stranger's imagined past | privacy (identifiability) | LOW | L2 |
| ch05.A04 / music lyrics (Love Yourz) + film quotes (Good Will Hunting, EEAAO) | copyright / fair use | LOW–MEDIUM | L3 |
| Bible translation quotations | copyright notice | LOW | L3, L8 |
| ch09.A05: composite case | ethics (disclosure) | LOW | L8 |
| Health-advice protocols (Sabbath, paradoxical intention, shame audit, relapse circuit-breaker) | health_claim, consumer_protection | MEDIUM | L6 |
