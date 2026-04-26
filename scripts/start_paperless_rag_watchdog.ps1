$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\paperless_rag_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*paperless_rag_watchdog.py*" }
if ($existing) {
  Write-Output "Paperless RAG watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 120 --stale-minutes 15 --notify-cooldown-minutes 30" -WindowStyle Hidden
Write-Output "Paperless RAG watchdog started."
