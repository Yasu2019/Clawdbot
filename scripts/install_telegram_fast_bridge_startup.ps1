$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$taskName = "ClawdbotTelegramFastBridge"
$scriptPath = Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1"
$runAsUser = $env:USERNAME

$action = "powershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`""

schtasks /Create `
  /TN $taskName `
  /SC ONLOGON `
  /TR $action `
  /RU $runAsUser `
  /RL LIMITED `
  /F | Out-Null

Write-Output "Scheduled task installed: $taskName"
