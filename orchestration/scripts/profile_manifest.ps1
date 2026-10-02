<#
.SYNOPSIS
  Write (default) or check (-Check) a sha256 manifest of every file under profile/.
  Muse-I runs -Check at every merge; any difference is a stop-the-line event (R-FOUND-02).
  Author edits are legitimate: after the author changes profile/, Muse-I rewrites the manifest
  and records the change in DECISIONS.md.
#>
param(
    [string]$ProfileDir = "C:\Users\ddrac\sots\profile",
    [string]$Manifest = "C:\Users\ddrac\sots-coord\profile_manifest.sha256",
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $ProfileDir).Path.TrimEnd('\')

$lines = Get-ChildItem -LiteralPath $root -Recurse -File |
    Sort-Object FullName |
    ForEach-Object {
        $rel = $_.FullName.Substring($root.Length).TrimStart('\').Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()
        "$hash  $rel"
    }

if (-not $Check) {
    $lines | Out-File -LiteralPath $Manifest -Encoding utf8
    Write-Host "Wrote $($lines.Count) entries to $Manifest"
    exit 0
}

if (-not (Test-Path -LiteralPath $Manifest)) { Write-Host "No manifest at $Manifest"; exit 1 }
$expected = Get-Content -LiteralPath $Manifest -Encoding utf8 | Where-Object { $_.Trim() -ne "" }
$diff = Compare-Object -ReferenceObject $expected -DifferenceObject $lines
if ($diff) {
    Write-Host "PROFILE CHANGED (stop the line):"
    $diff | ForEach-Object {
        $side = if ($_.SideIndicator -eq "<=") { "missing/changed (was)" } else { "new/changed (now)" }
        Write-Host "  $side  $($_.InputObject)"
    }
    exit 1
}
Write-Host "profile/ unchanged ($($lines.Count) files)"
exit 0
