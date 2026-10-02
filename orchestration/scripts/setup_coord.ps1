<#
.SYNOPSIS
  Create the SotS coordination folder (idempotent; never overwrites an existing file).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File orchestration\scripts\setup_coord.ps1
#>
param(
    [string]$CoordRoot = "C:\Users\ddrac\sots-coord"
)

$ErrorActionPreference = "Stop"
$agents = @("A", "B", "C", "D", "I")

function New-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Host "created  $Path"
    }
}

function New-FileIfMissing([string]$Path, [string]$Content) {
    if (-not (Test-Path -LiteralPath $Path)) {
        $Content | Out-File -LiteralPath $Path -Encoding utf8
        Write-Host "created  $Path"
    } else {
        Write-Host "kept     $Path"
    }
}

New-Dir $CoordRoot
foreach ($d in @("status", "broadcast", "cr", "contracts", "merge_queue", "reviews", "buildlog", "author_questions", "evidence", "inbox")) {
    New-Dir (Join-Path $CoordRoot $d)
}
foreach ($a in $agents) {
    New-Dir (Join-Path $CoordRoot "inbox\$a")
    New-Dir (Join-Path $CoordRoot "inbox\$a\done")
    New-Dir (Join-Path $CoordRoot "evidence\$a")
    New-FileIfMissing (Join-Path $CoordRoot "status\$a.md") "agent: Muse-$a`nwave: -`nstatus: not started`n"
}
foreach ($l in @("A", "B", "C", "D")) {
    New-FileIfMissing (Join-Path $CoordRoot "buildlog\$l.md") "# Staged BUILD_LOG lines for lane $l (moved into BUILD_LOG.md by Muse-I at each merge)`n"
}

New-FileIfMissing (Join-Path $CoordRoot "WAVE.md") "# Current wave`n`nwave: W0 (Muse-I stewarding the baseline; lanes must not start)`n"
New-FileIfMissing (Join-Path $CoordRoot "DEFERRED.md") @"
# Deferred-by-plan tasks (writer: Muse-I)

| Task | Lane | Waiting on | Lands in | State |
|---|---|---|---|---|
| T09.008 | B | A's classify/review_queue.py (P06) | W2 start | planned |
| T14.032 | C | K4 eval/run_eval.py (D) | W2 after K4 | planned |
| T15.074 | C | K4 eval/run_eval.py (D) | W2 after K4 | planned |
| T11A.032 | A | C's rewrite/style_guide.py (P15) | W3 start | planned |
"@
New-FileIfMissing (Join-Path $CoordRoot "DECISIONS.md") "# Decisions (append-only; writer: Muse-I)`n`nFormat: ## D-### yyyy-mm-dd - title / Context / Decision / Decided by / Consequences`n"
New-FileIfMissing (Join-Path $CoordRoot "contracts\CONTRACTS.md") @"
# Published contracts (writer: Muse-I)

| Id | Producer | Consumers | Interface | Version | main sha | Landed |
|---|---|---|---|---|---|---|
| K1 | A | C, B | models/foundation.py (T04A.001) | - | - | planned W1 |
| K2 | A | C | AgentCard.foundation_pieces (T04A.022) | - | - | planned W1 |
| K3 | D | B, C | acts/chapter_state.py (T13.003) | - | - | planned W2 |
| K4 | D | C, B | eval/run_eval.py + metric registry (T13.011) | - | - | planned W2 |
"@

if (-not (Test-Path -LiteralPath (Join-Path $CoordRoot ".git"))) {
    git -C $CoordRoot init | Out-Null
    git -C $CoordRoot add -A
    git -C $CoordRoot commit -q -m "coord: initial layout"
    Write-Host "git repo initialised in $CoordRoot"
}
Write-Host "Coordination folder ready: $CoordRoot"
