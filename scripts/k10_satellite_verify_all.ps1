#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot satellite CAE verification (K10). See docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$LavieIp = "100.87.244.46",
    [switch]$SkipDryRun
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
Set-Location $RepoRoot

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host ""
    Write-Host "== $Name =="
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "FAIL: $Name (exit $LASTEXITCODE)"
    }
    Write-Host "[PASS] $Name"
}

Invoke-Step "A1 live status" { python scripts\update_satellite_cae_live_status.py }
Invoke-Step "A2 router probe" { python scripts\cae_workload_router.py --probe-lavie-jobs --json }
Write-Host ""
Write-Host "== A3 exec_bridge (optional; job worker is primary for SJP-2) =="
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
python scripts\k10_verify_satellite_node.py --node-id lavie --ip $LavieIp 2>&1 | Out-Host
$a3Exit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($a3Exit -ne 0) {
    Write-Host "[WARN] A3 exec_bridge FAIL (n8n :5679). SJP-2 cae_trial may still PASS via :5680."
} else {
    Write-Host "[PASS] A3 exec_bridge"
}
Invoke-Step "A4 worker probe" { python scripts\k10_satellite_dispatch.py --probe --node lavie }

if (-not $SkipDryRun) {
    Invoke-Step "C1 lavie blanking dry-run" {
        python scripts\k10_satellite_cae_dispatch.py --category press_blanking --dry-run --host lavie
    }
    Invoke-Step "C2 lavie resin dry-run" {
        python scripts\k10_satellite_cae_dispatch.py --category resin_flow --dry-run --host lavie
    }
    Invoke-Step "C3 parallel dry-run" {
        python scripts\k10_parallel_cae_orchestrator.py --dry-run --or-max-trials 1 --of-max-trials 1
    }
}

Invoke-Step "D1 refresh portal status" { python scripts\update_satellite_cae_live_status.py --json | Out-Null }

Write-Host ""
Write-Host "RESULT: ALL PASS"
Write-Host "Portal: http://localhost:8088/portal.html"
Write-Host "Runbook: docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md"
