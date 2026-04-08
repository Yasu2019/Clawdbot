# watchdog_telegram_bridge.ps1
# Telegram bridge health check and auto-restart watchdog
# Run via Windows Task Scheduler every 5 minutes

param()

$repoRoot    = Split-Path -Parent $PSScriptRoot
$stateDir    = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile  = Join-Path $stateDir "harness_status.json"
$pidFile     = Join-Path $stateDir "bridge.pid"
$logFile     = Join-Path $stateDir "watchdog.log"
$startScript = Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1"

function Write-WLog {
    param([string]$msg)
    $ts   = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Start-Bridge {
    & powershell.exe -NonInteractive -ExecutionPolicy Bypass -File $startScript
}

# 1. No status file -> not running
if (-not (Test-Path $statusFile)) {
    Write-WLog "WARN: status file missing. Starting bridge..."
    Start-Bridge
    exit 0
}

# 2. Parse status
try {
    $status = [System.IO.File]::ReadAllText($statusFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
} catch {
    Write-WLog "ERROR: Cannot parse status file. Restarting..."
    Start-Bridge
    exit 0
}

$state     = $status.state
$updatedAt = $status.updatedAt
$pidVal    = [int]$status.pid

# 3. Check if process is alive
$processAlive = $false
if ($pidVal -gt 0) {
    $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue
    $processAlive = ($null -ne $proc)
}

if (-not $processAlive) {
    Write-WLog "WARN: bridge process (PID=$pidVal) not found. Restarting..."
    Start-Bridge
    exit 0
}

# 4. Check for stale status (hung process)
$lagMin = 999
try {
    $lastUpdate = [datetime]::Parse($updatedAt).ToUniversalTime()
    $lagMin     = ([datetime]::UtcNow - $lastUpdate).TotalMinutes
} catch {
    $lagMin = 999
}

if ($lagMin -gt 10) {
    Write-WLog "WARN: bridge stale ${lagMin}min (state=$state). Restarting..."
    Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 32
    Start-Bridge
    exit 0
}

# 5. poll_conflict for >2min -> restart to clear stale TCP connection
if ($state -eq "poll_conflict" -and $lagMin -gt 2) {
    Write-WLog "WARN: poll_conflict ${lagMin}min. Clearing TCP and restarting..."
    Stop-Process -Id $pidVal -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 32
    Start-Bridge
    exit 0
}

# 6. Healthy
Write-WLog "OK: bridge running (PID=$pidVal, state=$state, lag=${lagMin}min)"
