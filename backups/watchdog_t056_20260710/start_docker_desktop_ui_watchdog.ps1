$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\docker_desktop_ui_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*docker_desktop_ui_watchdog.py*"
}
if ($existing) {
  Write-Output "Docker Desktop UI watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 30 --quiet-recheck-seconds 30 --reset-cooldown-minutes 180" -WindowStyle Hidden
Write-Output "Docker Desktop UI watchdog started."
