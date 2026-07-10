$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\claudian_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*claudian_watchdog.py*" }
if ($existing) {
  Write-Output "Claudian watchdog already running."
  exit 0
}

$env:CLAWDBOT_REPO_ROOT = $repoRoot
Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 180 --stale-turn-minutes 2" -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Output "Claudian watchdog started."
