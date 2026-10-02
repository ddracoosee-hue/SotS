<#
.SYNOPSIS
  Create the lane worktrees for a wave (Muse-I only). Requires the tag w<Wave>-start on main.
  For W1 it creates the folders; for later waves each lane switches branch inside its existing
  worktree (git switch -c lane/<x>/w<k> w<k>-start), so this script only creates missing ones.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File orchestration\scripts\new_worktrees.ps1 -Wave 1
#>
param(
    [Parameter(Mandatory = $true)][int]$Wave,
    [string]$RepoRoot = "C:\Users\ddrac\sots",
    [string]$WtRoot = "C:\Users\ddrac\sots-wt",
    [string[]]$Lanes = @("A", "B", "C", "D"),
    [switch]$SkipGate
)

$ErrorActionPreference = "Stop"
$startTag = "w$Wave-start"

git -C $RepoRoot rev-parse --verify --quiet "refs/tags/$startTag" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Tag $startTag not found in $RepoRoot. Finish the previous merge first." }

$profileSrc = Join-Path $RepoRoot "profile"
if (-not (Test-Path -LiteralPath $profileSrc)) { throw "No profile/ in $RepoRoot" }
if (-not (Test-Path -LiteralPath $WtRoot)) { New-Item -ItemType Directory -Path $WtRoot | Out-Null }

$results = @()
foreach ($lane in $Lanes) {
    $path = Join-Path $WtRoot $lane
    $branch = "lane/$($lane.ToLower())/w$Wave"

    if (Test-Path -LiteralPath $path) {
        Write-Host "[$lane] worktree exists at $path - the lane switches itself: git switch -c $branch $startTag"
    } else {
        git -C $RepoRoot worktree add -b $branch $path $startTag
        if ($LASTEXITCODE -ne 0) { throw "[$lane] git worktree add failed" }
    }

    # Read-only view of the author's foundation (R-FOUND-02). Never delete recursively through it.
    $junction = Join-Path $path "profile"
    if (-not (Test-Path -LiteralPath $junction)) {
        New-Item -ItemType Junction -Path $junction -Target $profileSrc | Out-Null
        Write-Host "[$lane] profile junction -> $profileSrc"
    }

    Push-Location $path
    try {
        uv sync --locked
        if ($LASTEXITCODE -ne 0) { throw "[$lane] uv sync --locked failed" }
        uv run sots init
        if ($LASTEXITCODE -ne 0) { throw "[$lane] sots init failed" }
        $ok = $true
        if (-not $SkipGate) {
            & (Join-Path $path "orchestration\scripts\verify_lane.ps1") -Root $path
            $ok = ($LASTEXITCODE -eq 0)
        }
        $results += [pscustomobject]@{ Lane = $lane; Path = $path; Branch = $branch; Gate = $(if ($SkipGate) { "skipped" } elseif ($ok) { "GREEN" } else { "RED" }) }
    } finally {
        Pop-Location
    }
}

$results | Format-Table -AutoSize
if ($results | Where-Object { $_.Gate -eq "RED" }) { exit 1 }
