$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\p009_self_growth_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*p009_self_growth_watchdog.py*"
}
if ($existing) {
  Write-Output "P009/self-growth watchdog already running."
  exit 0
}

Start-Process -FilePath "python" -ArgumentList "`"$scriptPath`" --poll-seconds 1800" -WindowStyle Hidden
Write-Output "P009/self-growth watchdog started."
