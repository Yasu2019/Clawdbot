$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\ai_strategy_scout_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*ai_strategy_scout_watchdog.py*"
}
if ($existing) {
  Write-Output "AI strategy scout watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 1800 --stale-hours 20" -WindowStyle Hidden
Write-Output "AI strategy scout watchdog started."
