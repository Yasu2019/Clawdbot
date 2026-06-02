#Requires -Version 5.1
<#
.SYNOPSIS
  Restart LAVIE job worker ONLY (port 5680). Does NOT touch docker compose / OpenFOAM / OpenRadioss.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\lavie_usb_pack\scripts\lavie_restart_job_worker_only.ps1
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$RepoRoot = "",
    [int]$WorkerPort = 5680
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$workerScript = Join-Path $RepoRoot "scripts\lavie_start_job_worker.ps1"
if (-not (Test-Path $workerScript)) {
    throw "Missing: $workerScript"
}

Write-Host "[worker-only] Stopping listener on port $WorkerPort (python job worker only)..."
$conns = Get-NetTCPConnection -LocalPort $WorkerPort -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $conns) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match "python") {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Stopped PID $($proc.Id)"
    }
}
Start-Sleep -Seconds 1

Write-Host "[worker-only] Starting job worker (docker/FEM containers unchanged)..."
Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", $workerScript,
    "-InstallRoot", $InstallRoot,
    "-RepoRoot", $RepoRoot
) -WindowStyle Normal

Start-Sleep -Seconds 3
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:$WorkerPort/healthz" -UseBasicParsing -TimeoutSec 8
    Write-Host "[OK] healthz: $($health.Content)"
    Write-Host "WORKER_ONLY_RESTART_OK"
} catch {
    Write-Host "[!!] Worker not ready yet: $_"
    Write-Host "WORKER_ONLY_RESTART_QUEUED"
}
