$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bridgePath = Join-Path $repoRoot "scripts\telegram_fast_bridge.js"
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$pidFile = Join-Path $stateDir "bridge.pid"
$nodeCmd = (Get-Command node -ErrorAction Stop).Source

if (Test-Path $pidFile) {
  try {
    $existingPid = [int](Get-Content $pidFile -Raw)
  } catch {
    $existingPid = 0
  }

  if ($existingPid -gt 0) {
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
  }

  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $nodeCmd `
  -ArgumentList @($bridgePath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden

Write-Output "telegram_fast_bridge started"
