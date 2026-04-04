$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\email_continuous_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*email_continuous_watchdog.py*"
}
if ($existing) {
  Write-Output "Email continuous watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 60 --stale-minutes 15 --notify-cooldown-minutes 30" -WindowStyle Hidden
Write-Output "Email continuous watchdog started."
