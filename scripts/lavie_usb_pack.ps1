#Requires -Version 5.1
<#
.SYNOPSIS
  Stage minimal LAVIE setup files for USB copy or network push.

.EXAMPLE
  .\scripts\lavie_usb_pack.ps1
  Copy dist\lavie_usb_pack to USB, then on LAVIE run scripts\lavie_setup.bat
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "dist\lavie_usb_pack"
}

$required = @(
    "scripts\lavie_setup.bat",
    "scripts\lavie_node_setup.ps1",
    "scripts\lavie_trial_verify.bat",
    "scripts\satellite_deploy_exec_bridge.py",
    "deploy\satellite_node\docker-compose.yml",
    ".env"
)

foreach ($rel in $required) {
    $full = Join-Path $RepoRoot $rel
    if (-not (Test-Path $full)) {
        throw "Missing required file: $full"
    }
}

if (Test-Path $OutDir) {
    Remove-Item -LiteralPath $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

robocopy (Join-Path $RepoRoot "deploy\satellite_node") (Join-Path $OutDir "deploy\satellite_node") /E /NFL /NDL /NJH /NJS /NC /NS | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy satellite_node failed: $LASTEXITCODE" }

New-Item -ItemType Directory -Path (Join-Path $OutDir "scripts") -Force | Out-Null
foreach ($rel in @(
    "scripts\lavie_setup.bat",
    "scripts\lavie_node_setup.ps1",
    "scripts\lavie_repair_env.ps1",
    "scripts\lavie_trial_verify.bat",
    "scripts\lavie_job_worker.py",
    "scripts\lavie_start_job_worker.ps1",
    "scripts\lavie_start_job_worker.bat",
    "scripts\k10_satellite_dispatch.py",
    "scripts\k10_satellite_cae_dispatch.py",
    "scripts\cae_te_remote_trial.py",
    "scripts\cae_te_engine.py",
    "scripts\cae_te_paraview_capture.py",
    "scripts\cae_te_visual_report.py",
    "scripts\cae_te_optimizer.py",
    "scripts\cae_self_growth_gates.py",
    "scripts\lavie_boost_apply.ps1",
    "scripts\lavie_restart_all.ps1",
    "scripts\lavie_restart_remote.ps1",
    "scripts\lavie_n8n_restart.ps1",
    "scripts\satellite_deploy_exec_bridge.py"
)) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot $rel) -Destination (Join-Path $OutDir $rel) -Force
}

Copy-Item -LiteralPath (Join-Path $RepoRoot ".env") -Destination (Join-Path $OutDir ".env") -Force

$pvScriptsSrc = Join-Path $RepoRoot "scripts\pv_scripts"
$pvScriptsDst = Join-Path $OutDir "scripts\pv_scripts"
if (Test-Path $pvScriptsSrc) {
    New-Item -ItemType Directory -Path $pvScriptsDst -Force | Out-Null
    Copy-Item -Path (Join-Path $pvScriptsSrc "*") -Destination $pvScriptsDst -Recurse -Force
}

$guardSrc = Join-Path $RepoRoot "data\workspace\outbound_delivery_guard.py"
$guardDstDir = Join-Path $OutDir "data\workspace"
if (Test-Path $guardSrc) {
    New-Item -ItemType Directory -Path $guardDstDir -Force | Out-Null
    Copy-Item -LiteralPath $guardSrc -Destination (Join-Path $guardDstDir "outbound_delivery_guard.py") -Force
}

$readme = @"
LAVIE setup pack (minimal)
==========================

1. Copy this whole folder to LAVIE, e.g.:
   C:\Clawdbot_Docker_20260125

2. Start Docker Desktop on LAVIE.

3. Admin PowerShell on LAVIE:
   cd C:\lavie_usb_pack
   scripts\lavie_setup.bat

   If docker compose fails with unexpected character near NODE_ID:
   powershell -ExecutionPolicy Bypass -File scripts\lavie_repair_env.ps1
   cd C:\clawstack_satellite
   docker compose build
   docker compose up -d

4. On K10 after setup:
   .\scripts\k10_register_lavie_ip.ps1 -LavieIp 192.168.3.123
"@
Set-Content -Path (Join-Path $OutDir "README_LAVIE_SETUP.txt") -Value $readme -Encoding UTF8

Write-Host "[OK] Pack ready: $OutDir"
Write-Host "Copy to USB or LAVIE, then run scripts\lavie_setup.bat on LAVIE."
