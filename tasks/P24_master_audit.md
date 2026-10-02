# P24 — Master Audit (final build section; a low-frequency milestone tool)

**Prerequisites:** P23 (evaluation + live shakedown). **Blueprint refs:** 28 (all), 27, 26 (the Promise Ledger).
This is the **last build phase**. It is built fully, but the author runs it rarely: at a full draft, pre-submission, and pre-publication.

## Sections (input granularity)
- [ ] **T24.001** | `models/section.py` + `ingest/sections.py` | The Section model (28 §1); page estimate (settings.words_per_page = 325); warn at > 60 pages and suggest a split; sections map to chapters. | Tests (the Ch1 file ≈ 50 pages → no warning).
- [ ] **T24.002** | `pipeline/dry_run.py` | A per-section cost estimate across Acts 0–VI + reasoning + the audit. | Test.

## Test battery (CCAT)
- [ ] **T24.010** | `audit/families/*.py` | Deterministic families: T-TRUTH, T-CONSIST (deterministic part), T-DEPEND, T-VOICE, T-FRAME, T-LEGAL, T-LOAD, T-REPEAT, T-CHALLENGE, T-PROMISE, T-FORM (structure part). | A test per family.
- [ ] **T24.011** | `audit/families/mge_graded.py` | MGE-graded families: T-INTENT, T-ARC, T-SAFE (judged part), T-REFERENCE, T-CONSIST entailment, T-CROSS evaluation. | FakeProvider tests.
- [ ] **T24.012** | `prompts/audit/probe_gen.v1.md` + `audit/testgen.py` | T-CROSS probe generation over message pairs and chapter pairs sharing a concept (capped); the author-review step marks probes out of scope. | Test.
- [ ] **T24.013** | `prompts/audit/fixture_gen.v1.md` + `audit/testgen.py` | Test-of-the-test: a known-good + known-bad fixture per test (mutations: a flipped claim, a removed belief marker, a wrong NASB word, a forward reference, a changed number, a broken promise); non-discriminating tests discarded + logged. | Tests: a deliberately weak test gets discarded.
- [ ] **T24.014** | `audit/battery.py` | Freeze the battery as `eval/master_battery/v<N>/` with a hash; rebuild vN+1 when the foundation version changes. | Tests.

## Run, certify, export
- [ ] **T24.020** | `audit/runner.py` | The run sequence (28 §3): preconditions (Act VI done or 'audit anyway'), deterministic → MGE-graded → whole-book audience panel in reading order → aggregate. | Integration test on a 2-chapter fixture book.
- [ ] **T24.021** | `audit/certify.py` | Certification levels (MASTER / CANDIDATE / NOT READY); critical families = TRUTH, FRAME, SAFE, LEGAL, DEPEND (+ PROMISE for MASTER). | Boundary tests.
- [ ] **T24.022** | `reports/master_audit.py` | MASTER_AUDIT.md (every failing test with its location + fix direction) + master_certificate.json (battery/engine versions, scores, hashes). Fixes flow back as Proposals or revision notes: **no automatic rewriting**. | Snapshot test.
- [ ] **T24.023** | `reports/manuscript.py` | The Master Version export stamped with the certificate; F18 replay reproduces the audit. | Test.
- [ ] **T24.024** | `cli.py` + `tui/screens/master_audit.py` (built here, since P22 precedes) | `sots master-audit [--sections …|--book] [--dry-run]` with a cost confirmation; the TUI screen shows the battery, results, certification, and history. | Tests + Pilot test.
- [ ] **T24.090** | — | All green; BUILD_LOG line. | Done.
