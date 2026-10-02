<#
.SYNOPSIS
  Create the lane branches for a wave (Muse-I only; serial in-repo mode D-008).
  Requires the tag w<Wave>-start on main. Branches are cheap pointers; the single
  checkout does lanes serially, one branch at a time. Idempotent: existing
  branches are kept.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File orchestration\scripts\new_branches.ps1 -Wave 1
#>
param(
    [Parameter(Mandatory = $true)][int]$Wave,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." | Join-Path -ChildPath "..")).Path,
    [string[]]$Lanes = @("A", "B", "C", "D")
)

$ErrorActionPreference = "Stop"
$startTag = "w$Wave-start"

git -C $RepoRoot rev-parse --verify --quiet "refs/tags/$startTag" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Tag $startTag not found in $RepoRoot. Finish the previous merge first." }
$sha = (git -C $RepoRoot rev-parse --short $startTag).Trim()

$results = @()
foreach ($lane in $Lanes) {
    $branch = "lane/$($lane.ToLower())/w$Wave"
    git -C $RepoRoot rev-parse --verify --quiet "refs/heads/$branch" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $state = "kept"
    } else {
        git -C $RepoRoot branch $branch $startTag
        if ($LASTEXITCODE -ne 0) { throw "[$lane] git branch failed" }
        $state = "created"
    }
    $results += [pscustomobject]@{ Lane = $lane; Branch = $branch; Base = "$startTag ($sha)"; State = $state }
}

$results | Format-Table -AutoSize
Write-Host "Lane branches ready. Work them serially: git switch <branch>, build, gate, READY ticket, switch back."
