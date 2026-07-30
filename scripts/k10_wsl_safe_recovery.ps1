param(
    [string]$Repository = "D:\Clawdbot_Docker_20260125"
)

$ErrorActionPreference = "Stop"
$stateDir = Join-Path $Repository "data\state\wsl_storage_guard"
$resultPath = Join-Path $stateDir "recovery.json"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-RecoveryResult {
    param([string]$Status, [string]$Detail)
    @{
        checked_at = (Get-Date).ToString("o")
        status = $Status
        detail = $Detail
    } | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding utf8
}

& (Join-Path $Repository ".venv\Scripts\python.exe") `
    (Join-Path $Repository "scripts\k10_wsl_storage_guard.py") --json | Out-Null
$status = Get-Content -LiteralPath (Join-Path $stateDir "status.json") -Raw | ConvertFrom-Json
if ($status.severity -ne "healthy") {
    Write-RecoveryResult "deferred" "Host storage is not healthy; WSL restart is forbidden."
    exit 2
}

$probe = Start-Process -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu", "--", "true") `
    -WindowStyle Hidden -Wait -PassThru
if ($probe.ExitCode -eq 0) {
    Write-RecoveryResult "healthy" "Ubuntu probe succeeded; no recovery was performed."
    exit 0
}

$activeCae = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "k10_tri_track_cae_orchestrator|starter_win64|engine_win64|OpenRadioss"
}
if ($activeCae) {
    Write-RecoveryResult "deferred" "WSL failed but active CAE work exists; automatic restart is forbidden."
    exit 3
}

$desktopStatus = (& docker desktop status 2>&1 | Out-String)
if ($desktopStatus -match "running|starting") {
    Write-RecoveryResult "deferred" "Docker Desktop is active; automatic WSL restart is forbidden."
    exit 3
}

$last = Get-Item -LiteralPath $resultPath -ErrorAction SilentlyContinue
if ($last -and $last.LastWriteTime -gt (Get-Date).AddMinutes(-30)) {
    Write-RecoveryResult "cooldown" "A recovery decision was recorded within 30 minutes; retry suppressed."
    exit 4
}

& wsl --shutdown
Restart-Service -Name WslService
$retry = Start-Process -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu", "--", "true") `
    -WindowStyle Hidden -Wait -PassThru
if ($retry.ExitCode -ne 0) {
    Write-RecoveryResult "failed" "One bounded recovery attempt failed; manual investigation is required."
    exit 5
}

Write-RecoveryResult "recovered" "One bounded WSL service recovery succeeded."
exit 0
