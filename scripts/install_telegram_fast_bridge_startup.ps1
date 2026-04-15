$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$startupTaskName = "ClawdbotTelegramFastBridge"
$watchdogTaskName = "ClawstackTelegramBridgeWatchdog"
$startupScriptPath = Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1"
$watchdogScriptPath = Join-Path $repoRoot "scripts\watchdog_telegram_bridge.ps1"
$startupCmdSource = Join-Path $repoRoot "scripts\telegram_fast_bridge_startup.cmd"
$startupFolder = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmdTarget = Join-Path $startupFolder "telegram_fast_bridge_startup.cmd"
$runAsUser = $env:USERNAME

$startupAction = "powershell.exe -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startupScriptPath`""
$watchdogAction = "powershell.exe -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$watchdogScriptPath`""
$startupMode = "scheduled_task"

New-Item -ItemType Directory -Force -Path $startupFolder | Out-Null

try {
  schtasks /Create `
    /TN $startupTaskName `
    /SC ONLOGON `
    /TR $startupAction `
    /RU $runAsUser `
    /RL LIMITED `
    /F | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "schtasks startup install failed with exit code $LASTEXITCODE"
  }
} catch {
  Copy-Item -Path $startupCmdSource -Destination $startupCmdTarget -Force
  $startupMode = "startup_folder_fallback"
}

schtasks /Create `
  /TN $watchdogTaskName `
  /SC MINUTE `
  /MO 5 `
  /TR $watchdogAction `
  /RU $runAsUser `
  /RL LIMITED `
  /F | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "schtasks watchdog install failed with exit code $LASTEXITCODE"
}

Write-Output "Telegram bridge startup mode: $startupMode"
Write-Output "Scheduled tasks installed: $watchdogTaskName"
