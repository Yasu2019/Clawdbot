$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile = Join-Path $stateDir "harness_status.json"
$pidFile = Join-Path $stateDir "bridge.pid"

Write-Output "Bridge process:"
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*telegram_fast_bridge.ps1*" -or $_.CommandLine -like "*telegram_fast_bridge_v2.ps1*" -or $_.CommandLine -like "*telegram_fast_bridge_v3.ps1*" } |
  Select-Object ProcessId, Name, CommandLine

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
