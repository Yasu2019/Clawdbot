$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\central_patrol_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*central_patrol_watchdog.py*"
}
if ($existing) {
  Write-Output "Central Patrol Watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden
Write-Output "Central Patrol Watchdog started (High Frequency Patrol)."
