$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$statusFile = Join-Path $stateDir "harness_status.json"
$pidFile = Join-Path $stateDir "bridge.pid"
$canonicalBridge = Join-Path $repoRoot "scripts\telegram_fast_bridge.js"

function Get-BridgeProcesses {
  $escapedRepoRoot = [regex]::Escape($repoRoot)
  @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match $escapedRepoRoot -and
    $_.CommandLine -match 'telegram_fast_bridge'
  } | Select-Object ProcessId, Name, CommandLine, @{
    Name = "Implementation";
    Expression = {
      if ($_.CommandLine -match [regex]::Escape($canonicalBridge)) { "canonical_js" }
      elseif ($_.CommandLine -match 'telegram_fast_bridge_v\d+\.ps1') { "legacy_ps_variant" }
      elseif ($_.CommandLine -match 'telegram_fast_bridge\.ps1') { "legacy_ps" }
      else { "unknown" }
    }
  })
}

Write-Output "Bridge process:"
if (Test-Path $pidFile) {
  try {
    $bridgePid = [int](Get-Content $pidFile -Raw)
    Get-Process -Id $bridgePid | Select-Object Id, ProcessName, StartTime
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

Write-Output ""
Write-Output "Observed bridge command lines:"
$processes = @(Get-BridgeProcesses)
if ($processes.Count -gt 0) {
  $processes | Format-Table -AutoSize
} else {
  Write-Output "missing"
}
