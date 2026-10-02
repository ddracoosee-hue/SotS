# P22 — Terminal UI (Textual)

**Prerequisites:** P21. **Blueprint refs:** 12 (all).

## Shell
- [ ] **T22.001** | `tui/app.py` | The App with the header (book, run, tokens, provider health), sidebar, main area, and status line; subscribes to the events. | A Pilot test: the app starts with a seeded DB.
- [ ] **T22.002** | `tui/theme.py` | Color tokens: the origin colors (AUTHOR/SOURCE/SYSTEM), verdict label colors, severity colors; each label always shows text as well (never color alone). | A unit test on the label renderers.
- [ ] **T22.003** | `tui/workers.py` | Long tasks run in Textual workers; progress from the events; cancel via the kill switch. | A test: the UI stays responsive during a fake 5 s stage.
- [ ] **T22.004** | `tui/widgets/banners.py` | The safety notice banner (dismissible) and the legal banner (persistent on legal screens). | Tests.
- [ ] **T22.005** | `tests/fixtures/seed_db.py` | A seeded DB fixture covering every screen (1 book, 2 chapters at different acts, claims, media, findings, revisions, reactions, legal issues, proposals). | Used by every TUI test.

## Screens: analysis (12 §2.2)
- [ ] **T22.010** | `screens/home.py` | Home. | Pilot test.
- [ ] **T22.011** | `screens/ingest.py` | Ingest (file picker + paste + chapter select). | Pilot test.
- [ ] **T22.012** | `screens/runs.py` | Runs with live progress. | Pilot test.
- [ ] **T22.013** | `screens/claims.py` + `screens/claim_detail.py` | Claims table + detail. | Pilot tests.
- [ ] **T22.014** | `screens/media.py` | Media cards + work confirmation. | Pilot test.
- [ ] **T22.015** | `screens/psyche.py` | Board, synthesis, heat strip. | Pilot test.
- [ ] **T22.016** | `screens/messages_voice.py` | Coverage, gaps, drift map, voice. | Pilot test.
- [ ] **T22.017** | `screens/shadow_goals.py` | Question cards, rubric, sparklines, audit, waivers. | Pilot test.
- [ ] **T22.018** | `screens/expansion.py` | The concept map / threads / reports / margin / chat tabs. | Pilot test.
- [ ] **T22.019** | `screens/review_queue.py` | Low-confidence units, unresolved works, dead letters (with retry). | Pilot test.
- [ ] **T22.020** | `screens/profile.py` + `screens/interview.py` | Profile view/edit + the TUI interview. | Pilot tests.
- [ ] **T22.021** | `screens/settings.py` | Read-only config + provider tests + doctor results. | Pilot test.

## Screens: workshop (12 §3.2)
- [ ] **T22.030** | `screens/chapter_board.py` | Act progress + gate lights + blocked reasons. | Pilot test.
- [ ] **T22.031** | `screens/style_guide.py` | Edit/approve the Style Guide. | Pilot test.
- [ ] **T22.032** | `screens/revision_review.py` | Side-by-side hunks; accept/reject/undo/bulk. | Pilot test with key presses.
- [ ] **T22.033** | `screens/style_crosscheck.py` | The reports view. | Pilot test.
- [ ] **T22.034** | `screens/audience_lab.py` | Scorecards, journey curve, hotspots, reactions, the "Simulated readers" label. | Pilot test + a label assertion.
- [ ] **T22.035** | `screens/persona_studio.py` | Persona edit + coverage matrix + the adults-only validation message. | A Pilot test: entering age 17 shows an error and does not save.
- [ ] **T22.036** | `screens/legal_chamber.py` | Issues, memos, endorsements, dissents, transcripts, waiver flow. | Pilot test.
- [ ] **T22.037** | `screens/proposal_desk.py` | Cards, accept flow (pick P#/M# + answer questions), modify/defer/reject, chat. | Pilot test with the full accept path.
- [ ] **T22.038** | `screens/below_bar.py` | The archive + promote. | Pilot test.
- [ ] **T22.039** | `screens/grader_health.py` | Health signals. | Pilot test.
- [ ] **T22.040** | `screens/learning_inbox.py` | Apply/dismiss/rollback. | Pilot test.
- [ ] **T22.042** | `screens/block_synthesis.py` + `screens/foundation.py` | Block Synthesis screen (T14A.025) + Foundation screen (anchors with verification status, architecture/reading order, messages, dictation coverage, FoundationChange history). | Pilot tests.
- [ ] **T22.043** | `screens/reason.py`, `screens/intent.py`, `screens/grade_inspector.py`, `screens/manuscript.py`, the Revise-with-note widget, the Recheck & Reason button + reminder | Specs in 12 §4. | Pilot tests: the reminder shows quietly; no screen offers "regenerate". |
- [ ] **T22.044** | `screens/voice_lab.py` | The Voice Lab screen per T11A.040 / 29 §6 / 12 §4: add material + what-changed diff, profile view, pin/relax/forbid, the "sound like me?" check, one-key not-me (with confirmation), snapshots/rollback; the Home-screen Voice Lab line. | Pilot tests: adding a fixture sample shows a non-empty diff; pin survives a model rebuild; not-me asks before writing to `not_me/`.
- [ ] **T22.041** | `screens/export.py` | Export status + trigger. | Pilot test.

## Polish
- [ ] **T22.050** | `tui/keys.py` | A central keybinding map; a help overlay (`?`) listing the keys per screen. | Test.
- [ ] **T22.051** | `tui/app.py` | Remember the last screen/filters per user in `data/tui_state.json` (try/except around every read/write). | Test.
- [ ] **T22.052** | — | **[author verifies]** Usability pass on the author's terminal; record the feedback in 15_OPEN_ITEMS §C. | The author confirms.
- [ ] **T22.090** | — | All green; BUILD_LOG line. | Done.
