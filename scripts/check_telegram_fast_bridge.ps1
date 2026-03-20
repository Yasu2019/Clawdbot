$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile = Join-Path $stateDir "harness_status.json"
$pidFile = Join-Path $stateDir "bridge.pid"

Write-Output "Bridge process:"
if (Test-Path $pidFile) {
  try {
    $pid = [int](Get-Content $pidFile -Raw)
    Get-Process -Id $pid | Select-Object Id, ProcessName, StartTime
  } catch {
    Write-Output "missing or stale"
  }
} else {
  Write-Output "missing"
}

Write-Output ""
Write-Output "PID file:"
if (Test-Path $pidFile) {
  Get-Content $pidFile
} else {
  Write-Output "missing"
}

Write-Output ""
Write-Output "Status file:"
if (Test-Path $statusFile) {
  Get-Content $statusFile
} else {
  Write-Output "missing"
}
