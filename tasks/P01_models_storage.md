# P01 — Models + Storage

**Prerequisites:** P00. **Blueprint refs:** 03, 11 §3, 16 §2.2, 17 §4, 18 §2, 19 §1.1, 19 §1.2, 19 §5, 20 §3–§6, 22 §5, 02 §5.

## Models (one file per group; all `frozen=True, extra="forbid"` unless marked mutable)
- [x] **T01.001** | `models/ids.py` | `new_id(prefix)` using ULID (implement the ULID locally with `os.urandom` + time; no new dependency). | Tests: the prefix is kept; 10k ids are unique and sortable by time.
- [x] **T01.002** | `models/enums.py` | All enums from 03 §1 + Origin (11 §3). Add `Verdict.strength()` returning the order index. | Test: the strength order matches 03 §1.
- [x] **T01.003** | `models/document.py` | Document, Chunk. | Round-trip test.
- [x] **T01.004** | `models/unit.py` | Unit (mutable), including parent_unit_id, labeled_by, and `revision_offsets: dict[str, tuple[int,int]]` (19 §1.1). | Round-trip test.
- [x] **T01.005** | `models/evidence.py` | Evidence, FetchedDoc, SearchHit. | Round-trip test.
- [x] **T01.006** | `models/verdict.py` | RuleCheck, VerdictRecord, SpecialistFindings, DiscoveryNote (06 §9). | Round-trip test.
- [x] **T01.007** | `models/media.py` | MediaWork, MediaPoint, MediaCheck. | Round-trip test.
- [x] **T01.008** | `models/psyche.py` | EngineFinding, Synthesis. | Round-trip test.
- [x] **T01.009** | `models/narrative.py` | CoreMessage, MessageMapping, DriftReport, VoiceFingerprint, VoiceComparison. | Round-trip test.
- [x] **T01.010** | `models/shadow.py` | ShadowItem, RubricScore, ShadowReport. | Round-trip test.
- [x] **T01.011** | `models/profile.py` | AuthorProfile, BookProfile (+ `media_exclusions`), ChapterBrief (+ an optional `reader_journey`). Mark provisional in the docstrings. | Round-trip test.
- [x] **T01.012** | `models/run.py` | Run (mutable), LLMCall, ChapterState (`chapter_id, act, gate_status: dict, blocked_reasons: list[str]`). | Round-trip test.
- [x] **T01.013** | `models/expansion.py` | Everything in 11 §3. | Round-trip test.
- [x] **T01.014** | `models/agents.py` | AgentCard, AgentAction, Observation, AgentRun, AgentResult[T], BudgetSlice (16). | Round-trip test; AgentCard rejects unknown failsafe ids.
- [x] **T01.015** | `models/grading.py` | CriterionResult, GradeRecord, GraderHealth (17 §4, §6). | Round-trip test.
- [x] **T01.016** | `models/proposal.py` | PlacementOption, IntegrationMode, AuthorQuestion, Proposal, ProposalDecision, IntegrationPlanItem (18). Validators: ≥ 2 placements, ≥ 2 modes, 2–5 questions. | Tests for each validator.
- [x] **T01.017** | `models/rewrite.py` | RevisionHunk, Revision, StyleGuide, StyleReport, CrossCheckItem, CrossCheckReport (19). | Round-trip test.
- [x] **T01.018** | `models/audience.py` | Persona (validator: age ≥ 18 → else AdultsOnlyViolation), QuoteRef, MechanicsFinding, PersonaReaction, AudienceBrief, AudienceScorecard, BriefItem, AudienceBrief, CalibrationRecord, PlaybookEntry (20). | Test: a persona with age 17 raises.
- [x] **T01.019** | `models/legal.py` | LegalIssue, Authority, Position, DefenseMemo (22 §5). | Round-trip test.
- [x] **T01.020** | `models/learning.py` | LearningChange (id, kind, target, before, after, evidence, status, applied_at), PromptTrial. | Round-trip test.
- [x] **T01.021** | `models/__init__.py` | Re-export all public models. | `from sots.models import *` works.

## Storage
- [x] **T01.030** | `storage/schema.sql` | One table per persisted model (JSON columns for list/dict fields), with indexes on run_id, document_id, unit_id, chapter_id, and status. Tables also for: summaries, llm_calls, cache, dead_letters, checkpoints, events, playbook, calibration, grader_health, prompt_trials, dialogues, waivers, chapter_state. | The schema applies cleanly to an empty DB.
- [x] **T01.031** | `storage/db.py` | `connect(path)` with WAL, foreign_keys=ON, row_factory; `migrate()` using the `schema_version` table + an ordered list of migration SQL files. | Test: migrate from empty → current; migrate again is a no-op.
- [x] **T01.032** | `storage/repo.py` | Typed `save_x` / `get_x` / `list_x(filters)` for every model. Generic helpers for JSON columns. **The only module with SQL** (lint rule in T01.040). | Round-trip tests for every model through the DB.
- [x] **T01.033** | `storage/repo.py` | `idempotent_save(model, key)` (F07): insert-or-ignore on the idempotency key. | Test: double save → one row.
- [x] **T01.034** | `storage/files.py` | Helpers for the inbox, revisions, and exports paths; atomic writes (write to a temp file + rename). | Test: an interrupted write never leaves a partial file.
- [x] **T01.035** | `storage/repo.py` | `snapshot_counts(run_id)` for invariant checks (used in F20). | Test.

## Lint guard
- [x] **T01.040** | `tests/unit/test_architecture.py` | A test that greps `src/` and fails if `sqlite3`/`execute(` appear outside `storage/`, or httpx/model SDK calls appear outside `providers/` and `agents/tools/`. | The test passes, and fails on a planted violation (verify, then remove the plant).

## Phase close
- [x] **T01.090** | — | All green; BUILD_LOG line. | Done.
