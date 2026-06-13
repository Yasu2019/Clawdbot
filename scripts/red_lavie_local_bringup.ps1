# Run ON Red LAVIE (admin PowerShell). Starts job_worker :5682 + monitor_agent :8111.
#
# This file lives on K10 at D:\Clawdbot_Docker_20260125\scripts\ — NOT on Red LAVIE.
# On Red LAVIE, download from K10 first:
#
#   $K10 = "http://100.119.18.40:8123"
#   $p = "$env:TEMP\red_lavie_local_bringup.ps1"
#   Invoke-WebRequest "$K10/red_lavie_local_bringup.ps1" -OutFile $p -UseBasicParsing
#   powershell -NoProfile -ExecutionPolicy Bypass -File $p -K10 $K10
#
# Or one step (Red LAVIE default ExecutionPolicy blocks -File without Bypass):
#   $K10 = "http://100.119.18.40:8123"
#   Invoke-WebRequest "$K10/red_lavie_bootstrap_from_k10.ps1" -OutFile $env:TEMP\bootstrap.ps1 -UseBasicParsing
#   powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\bootstrap.ps1 -K10 $K10
#
param(
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$Token = "",
    [int]$WorkerPort = 5682,
    [int]$MonitorPort = 8111
)

$ErrorActionPreference = "Stop"

function Test-Health($Url) {
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

Write-Host "=== Red LAVIE Local Bringup ==="

if (-not $Token) {
    $envFile = Join-Path $InstallRoot ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^SATELLITE_JOB_TOKEN=(.+)$') { $Token = $Matches[1].Trim() }
        }
    }
}
if (-not $Token) {
    Write-Host "[WARN] SATELLITE_JOB_TOKEN not set. Pass -Token or create $InstallRoot\.env"
}

$workerOk = Test-Health "http://127.0.0.1:$WorkerPort/healthz"
$monitorOk = Test-Health "http://127.0.0.1:$MonitorPort/metrics"
Write-Host "Before: worker=$workerOk monitor=$monitorOk"

if (-not $workerOk) {
    $startScript = Join-Path (Split-Path $MyInvocation.MyCommand.Path) "red_lavie_start_job_worker.ps1"
    if (-not (Test-Path $startScript)) {
        $startScript = Join-Path $InstallRoot "scripts\red_lavie_start_job_worker.ps1"
    }
    if (Test-Path $startScript) {
        if (-not $Token) { throw "Token required to start job worker" }
        & $startScript -K10 $K10 -Token $Token -InstallRoot $InstallRoot -Port $WorkerPort
    } else {
        throw "red_lavie_start_job_worker.ps1 not found"
    }
}

if (-not $monitorOk) {
    $monScript = Join-Path (Split-Path $MyInvocation.MyCommand.Path) "red_lavie_start_monitor.ps1"
    if (-not (Test-Path $monScript) -and $K10) {
        $monScript = Join-Path $env:TEMP "red_lavie_start_monitor.ps1"
        try {
            Invoke-WebRequest "$K10/red_lavie_start_monitor.ps1" -OutFile $monScript -UseBasicParsing -TimeoutSec 15
        } catch {
            Write-Host "[WARN] download red_lavie_start_monitor.ps1 failed: $_"
        }
    }
    if (Test-Path $monScript) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $monScript -K10 $K10 -AgentPath (Join-Path $InstallRoot "scripts\monitor_agent.py")
    } else {
        Write-Host "[WARN] red_lavie_start_monitor.ps1 not found; skip monitor"
    }
}

$workerOk = Test-Health "http://127.0.0.1:$WorkerPort/healthz"
$monitorOk = Test-Health "http://127.0.0.1:$MonitorPort/metrics"
Write-Host "After:  worker=$workerOk monitor=$monitorOk"

if (-not $workerOk) { throw "job_worker still down on :$WorkerPort" }

Write-Host "RED_LAVIE_LOCAL_BRINGUP_OK worker=http://127.0.0.1:$WorkerPort/healthz"
