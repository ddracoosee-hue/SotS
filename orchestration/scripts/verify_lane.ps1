<#
.SYNOPSIS
  The standard gate for a lane branch (serial mode D-013) or worktree: ruff, pyright,
  pytest (optionally twice and chaos), sots doctor, and the profile check
  (junction in a worktree, read-in-place in the main checkout).
  Exit code 1 if anything fails. Paste the summary into evidence logs.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File orchestration\scripts\verify_lane.ps1 -Twice
#>
param(
    [string]$Root = (Get-Location).Path,
    [switch]$Twice,
    [switch]$Chaos
)

$results = @()
function Invoke-Step([string]$Name, [scriptblock]$Block, [int[]]$OkCodes = @(0)) {
    $start = Get-Date
    & $Block
    $code = $LASTEXITCODE
    $secs = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
    $script:results += [pscustomobject]@{ Step = $Name; Exit = $code; Seconds = $secs; Result = $(if ($OkCodes -contains $code) { "PASS" } else { "FAIL" }) }
}

Push-Location $Root
try {
    $sha = (git rev-parse --short HEAD)
    $branch = (git rev-parse --abbrev-ref HEAD)

    Invoke-Step "ruff check ." { uv run ruff check . }
    Invoke-Step "pyright" { uv run pyright }
    Invoke-Step "pytest (run 1)" { uv run pytest -q }
    if ($Twice) { Invoke-Step "pytest (run 2)" { uv run pytest -q } }
    if ($Chaos) { Invoke-Step "pytest -m chaos" { uv run pytest -q -m chaos } -OkCodes @(0, 5) }
    Invoke-Step "sots doctor" { uv run sots doctor }

    $profileOk = $false
    $p = Join-Path $Root "profile"
    if (Test-Path -LiteralPath $p) {
        $item = Get-Item -LiteralPath $p -Force
        $isJunction = [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
        $isMainCheckout = Test-Path -LiteralPath (Join-Path $Root ".git") -PathType Container
        $profileOk = $isJunction -or $isMainCheckout
    }
    $results += [pscustomobject]@{ Step = "profile check"; Exit = $(if ($profileOk) { 0 } else { 1 }); Seconds = 0; Result = $(if ($profileOk) { "PASS" } else { "FAIL" }) }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Gate for $Root  [$branch @ $sha]  $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$results | Format-Table -AutoSize
if ($results | Where-Object { $_.Result -eq "FAIL" }) { exit 1 }
exit 0
