# Decisions (append-only; writer: Muse-I)

Format: ## D-### yyyy-mm-dd - title / Context / Decision / Decided by / Consequences

## D-001 2026-09-29 - AD-1: parallel lanes as an R-SCOPE-03 exception

Context: R-SCOPE-03 says build phases strictly in order; the real code
dependencies allow lane parallelism with merge gates.
Decision: Yes — four lanes build in parallel; each keeps strict order
inside the lane; cross-lane dependencies gate on merges.
Decided by: author (AD-1).
Consequences: WAVE_PLAN, ownership map, contracts, and the merge
procedure govern the build. D-013 later serializes execution without
changing this structure.

## D-002 2026-09-29 - AD-2: deferred-by-plan tasks allowed

Context: 4 tasks wait on another lane's file (WAVE_PLAN §4).
Decision: Yes — a phase may close as "closed-with-deferral" and close
fully when the deferred task lands.
Decided by: author (AD-2).
Consequences: DEFERRED.md tracks T09.008, T14.032, T15.074, T11A.032.

## D-003 2026-09-29 - AD-3: first git commit (baseline)

Context: worktrees need a commit; profile/ and data/ stay gitignored
per R-DATA-04.
Decision: Yes — commit everything except profile/, data/ (plus .env,
.venv, caches).
Decided by: author (AD-3).
Consequences: `b68221a` exists; W0 verifies it and adds `w0-baseline`.

## D-004 2026-09-29 - AD-4: Wave 0 splits files over 400 lines

Context: storage/repo.py, cli.py, agents/base.py, vault/notes.py exceed
R-CODE-03 and are merge hotspots.
Decision: Yes — split with no behaviour change; storage/repo.py
becomes the package storage/repo/ (R-CODE-03 overrides 02 §5 wording).
Decided by: author (AD-4).
Consequences: W0 step 4; logged in 15 §B.

## D-005 2026-09-29 - AD-5: R-CODE-03 scope is src only

Context: 5 test files and both SQL files also exceed 400 lines.
Decision: The limit applies to `src/**/*.py` only; tests and .sql
exempt. Logged in 15 §A.
Decided by: author (AD-5).
Consequences: the W0 guard test scans src only.

## D-006 2026-09-29 - AD-6: coordination folder path

Context: lanes need a shared folder outside every worktree, with
history. The scripts take -CoordRoot, so the path is a choice.
Decision: Yes to `C:\Users\ddrac\sots-coord\` with its own git repo.
Decided by: author (AD-6).
Consequences: setup_coord.ps1 defaults there. D-013 moves the live
folder to in-repo `coord/` (tracked by main history) under the
plan-blessed "pick another path" alternative; the scripts keep working
via -CoordRoot.

## D-007 2026-09-29 - AD-7: profile via read-only junction

Context: worktrees need profile/ without copies that drift.
Decision: Yes — each worktree reaches profile/ through a directory
junction to the main checkout; read-only by rule (R-FOUND-02), checked
by a sha256 manifest at every merge.
Decided by: author (AD-7).
Consequences: new_worktrees.ps1 creates junctions; profile_manifest.ps1
checks them. In D-013 serial mode there are no worktrees: the single
checkout reads profile/ directly (same rule, same manifest check).

## D-008 2026-10-02 - N-1: keep the parallel 4-lane plan

Context: Wave 0 found P04–P06 done; the question was whether to keep
parallel lanes (with the §3 changes) or switch to one agent building
phases in order (§4 fallback).
Decision: Parallel, as approved.
Decided by: author (N-1).
Consequences: lanes/branches/merges structure stands; D-013 serializes
only the execution.

## D-009 2026-10-02 - N-2: HTTP guard allowlist

Context: the T01.040 guard allows httpx only in providers/ and
agents/tools/, but blueprint 02 puts the httpx-using fetchers in
research/fetchers/.
Decision: Yes — add research/fetchers/ and research/search/ to the
allowlist. The folder tree is the more specific spec. Record in 15 §B.
Decided by: author (N-2).
Consequences: W0 step 5; the 12 P07 files pass, anything else fails.

## D-010 2026-10-02 - N-3: move P11 from Lane D to Lane A

Context: Lane A has no W1 work (P04–P06 done); P11 fits "Foundation &
Voice" and D's chain is the longest.
Decision: Yes — P11 (message ledger, drift, flow, voice fingerprint)
moves to A; P11A follows in Wave 2.
Decided by: author (N-3).
Consequences: ownership map moves P11's 7 narrative files +
map_messages prompt + narrative report section D→A.

## D-011 2026-10-02 - N-4: Lane B verifies and finishes P07

Context: P07 is ~40% present, 0/24 boxes, with lint/type errors.
Decision: Yes — leave it in place; Lane B verifies task by task and
completes it. It's committed, so nothing is lost if B redoes parts.
Decided by: author (N-4).
Consequences: W0 touches P07 only for the N-2 allowlist; the ruff 7 +
pyright 6 ride as known Lane-B items.

## D-012 2026-10-02 - AQ-W0-1: start from the beginning

Context: MUSE_START_HERE.md said "Nothing is coded yet. Start at P00"
(OI-04, author-owned) while P00–P06 were built.
Decision: Muse starts from the beginning and checks where and what was
left off; the stale line is replaced. Wave 0 step 3 re-verifies every
finished phase from P00 up.
Decided by: author (AQ-W0-1).
Consequences: full P00–P06 + P04A + vault re-verification in W0; no box
needed un-ticking.

## D-013 2026-10-02 - Serial in-repo execution mode

Context: the W0 agent runs sandboxed: it cannot write outside the repo
(sots-coord/, sots-wt/ unreachable) and there is no parallel agent
substrate (no worktrees, no tmux/host-manager lanes). The author asked
to reorganize past this without losing function.
Decision: keep the whole lane/wave/contract/merge/review structure and
run it serially in the one checkout: (a) coordination lives at in-repo
`coord/` (tracked; AD-6's blessed alt path; history via main instead of
a nested repo); (b) lanes work on `lane/<x>/w<k>` branches, not
worktrees (`scripts/new_branches.ps1`); (c) Muse-I executes each lane's
tasks serially, then merges per the wave merge order; (d) reviews read
the branch diff (no review checkout); the merge gate runs adversarial
probes and the full gate per lane merge; (e) `profile/` is read in
place under R-FOUND-02 with the manifest check at every merge (no
junctions); (f) each lane writes only its disjoint coord paths
(status/X.md, evidence/X/, buildlog/X.md, inbox/X/) so merges stay
clean; WAVE/CONTRACTS/DECISIONS/DEFERRED stay I-only.
Decided by: author (reorg request 2026-10-02, executed by Muse-I).
Consequences: W1+ runs fully in-repo. The worktree/junction scripts and
paths stay as the documented parallel alternative if the author later
runs several sessions. Doc updates: protocol §1, review procedure §6,
lane headers, integrator steps 8–10, NEXT_STEPS §0/steps 9–10.
