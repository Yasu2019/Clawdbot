# watchdog_telegram_bridge.ps1
# Telegram bridge health check and auto-restart watchdog
# Run via Windows Task Scheduler every 5 minutes

param()

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile = Join-Path $stateDir "harness_status.json"
$pidFile = Join-Path $stateDir "bridge.pid"
$logFile = Join-Path $stateDir "watchdog.log"
$startScript = Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1"
$canonicalBridge = Join-Path $repoRoot "scripts\telegram_fast_bridge.js"

function Write-WLog {
    param([string]$msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Output $line
    Add-Content -Path $logFile -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Start-Bridge {
    & powershell.exe -NonInteractive -ExecutionPolicy Bypass -File $startScript
}

function Get-BridgeProcesses {
    $escapedRepoRoot = [regex]::Escape($repoRoot)
    $canonicalPattern = [regex]::Escape($canonicalBridge)
    @(Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match $escapedRepoRoot -and
        $_.CommandLine -match 'telegram_fast_bridge'
    } | Select-Object ProcessId, Name, CommandLine, @{
        Name = "Implementation";
        Expression = {
            if ($_.CommandLine -match $canonicalPattern) { "canonical_js" }
            elseif ($_.CommandLine -match 'telegram_fast_bridge_v\d+\.ps1') { "legacy_ps_variant" }
            elseif ($_.CommandLine -match 'telegram_fast_bridge\.ps1') { "legacy_ps" }
            else { "unknown" }
        }
    })
}

function Restart-CanonicalBridge {
    param([string]$Reason)
    Write-WLog "WARN: $Reason Restarting canonical bridge..."
    $processes = Get-BridgeProcesses
    foreach ($proc in $processes) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $pidFile) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 3
    Start-Bridge
    exit 0
}

$bridgeProcesses = Get-BridgeProcesses
$canonicalProcesses = @($bridgeProcesses | Where-Object { $_.Implementation -eq "canonical_js" })
$legacyProcesses = @($bridgeProcesses | Where-Object { $_.Implementation -ne "canonical_js" })

if ($legacyProcesses.Count -gt 0) {
    $legacySummary = ($legacyProcesses | ForEach-Object { "$($_.ProcessId):$($_.Implementation)" }) -join ", "
    Restart-CanonicalBridge -Reason "unexpected legacy bridge implementation detected ($legacySummary)."
}

if ($canonicalProcesses.Count -gt 1) {
    $canonicalSummary = ($canonicalProcesses | ForEach-Object { $_.ProcessId }) -join ", "
    Restart-CanonicalBridge -Reason "multiple canonical bridge processes detected ($canonicalSummary)."
}

if (-not (Test-Path $statusFile)) {
    Write-WLog "WARN: status file missing. Starting bridge..."
    Start-Bridge
    exit 0
}

try {
    $status = [System.IO.File]::ReadAllText($statusFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
} catch {
    Write-WLog "ERROR: Cannot parse status file. Restarting..."
    Start-Bridge
    exit 0
}

$state = $status.state
$updatedAt = $status.updatedAt
$pidVal = [int]$status.pid
$canonicalPid = if ($canonicalProcesses.Count -eq 1) { [int]$canonicalProcesses[0].ProcessId } else { 0 }

if ($canonicalPid -le 0) {
    Restart-CanonicalBridge -Reason "canonical bridge process not found."
}

if ($pidVal -ne $canonicalPid) {
    Restart-CanonicalBridge -Reason "status pid $pidVal does not match canonical bridge pid $canonicalPid."
}

$processAlive = $false
if ($pidVal -gt 0) {
    $proc = Get-Process -Id $pidVal -ErrorAction SilentlyContinue
    $processAlive = ($null -ne $proc)
}

if (-not $processAlive) {
    Restart-CanonicalBridge -Reason "bridge process (PID=$pidVal) not found."
}

$lagMin = 999
try {
    $lastUpdate = [datetime]::Parse($updatedAt).ToUniversalTime()
    $lagMin = ([datetime]::UtcNow - $lastUpdate).TotalMinutes
} catch {
    $lagMin = 999
}

if ($lagMin -gt 10) {
    Restart-CanonicalBridge -Reason "bridge stale ${lagMin}min (state=$state)."
}

if ($state -eq "poll_conflict" -and $lagMin -gt 2) {
    Restart-CanonicalBridge -Reason "poll_conflict ${lagMin}min."
}

Write-WLog "OK: bridge running (PID=$pidVal, state=$state, lag=${lagMin}min, impl=canonical_js)"
