$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\obsidian_vault_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match "python" -and $_.CommandLine -like "*obsidian_vault_watchdog.py*"
}
if ($existing) {
  Write-Output "Obsidian vault watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 180 --cooldown-seconds 90" -WindowStyle Hidden
Write-Output "Obsidian vault watchdog started."
