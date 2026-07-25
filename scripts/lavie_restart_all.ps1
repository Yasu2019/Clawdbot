#Requires -Version 5.1
<#
.SYNOPSIS
  Boost LAVIE, restart satellite docker + job worker (run ON LAVIE, Admin recommended).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\lavie_usb_pack\scripts\lavie_restart_all.ps1
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$RepoRoot = "",
    [int]$WorkerPort = 5680,
    [switch]$SkipBoost
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$boostScript = Join-Path $RepoRoot "scripts\lavie_boost_apply.ps1"
$workerScript = Join-Path $RepoRoot "scripts\lavie_start_job_worker.ps1"

if (-not $SkipBoost) {
    if (-not (Test-Path $boostScript)) {
        throw "Missing boost script: $boostScript"
    }
    & $boostScript -InstallRoot $InstallRoot -RepoRoot $RepoRoot
}

Write-Host "[restart] Docker satellite stack..."
Push-Location $InstallRoot
try {
    docker compose down 2>&1 | Out-Host
    Start-Sleep -Seconds 2
    docker compose up -d 2>&1 | Out-Host
} finally {
    Pop-Location
}

Write-Host "[restart] Stopping job worker on port $WorkerPort..."
$conns = Get-NetTCPConnection -LocalPort $WorkerPort -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $conns) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match "python") {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Stopped PID $($proc.Id)"
    }
}
Start-Sleep -Seconds 2

Write-Host "[restart] Starting job worker..."
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $workerScript,
    "-InstallRoot", $InstallRoot,
    "-RepoRoot", $RepoRoot
) -WindowStyle Hidden

Start-Sleep -Seconds 3
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$WorkerPort/healthz" -UseBasicParsing -TimeoutSec 8
    if ($health.StatusCode -eq 200) {
        Write-Host "[OK] Job worker healthz: $($health.Content)"
    }
} catch {
    Write-Host "[!!] Worker not ready yet. Check task logs."
}

Write-Host "[OK] LAVIE restart complete (boost + docker + worker)"
