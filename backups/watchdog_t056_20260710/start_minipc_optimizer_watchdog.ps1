$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\minipc_optimizer_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*minipc_optimizer_watchdog.py*"
}
if ($existing) {
  Write-Output "Mini PC optimizer watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 600 --free-gb-threshold 10 --free-percent-threshold 20 --cooldown-minutes 180" -WindowStyle Hidden
Write-Output "Mini PC optimizer watchdog started."
