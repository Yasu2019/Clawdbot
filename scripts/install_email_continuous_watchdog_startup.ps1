$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$taskNameBoot = "ClawdbotEmailContinuousWatchdogBoot"
$taskNameLogon = "ClawdbotEmailContinuousWatchdogLogon"
$scriptPath = Join-Path $repoRoot "scripts\start_email_continuous_watchdog.ps1"
$runAsUser = $env:USERNAME
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmd = Join-Path $startupDir "ClawdbotEmailContinuousWatchdog.cmd"

$action = "powershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`""

$taskErrors = @()
try {
  schtasks /Create `
    /TN $taskNameBoot `
    /SC ONSTART `
    /TR $action `
    /RU SYSTEM `
    /RL HIGHEST `
    /F | Out-Null
} catch {
  $taskErrors += "ONSTART"
}

try {
  schtasks /Create `
    /TN $taskNameLogon `
    /SC ONLOGON `
    /TR $action `
    /RU $runAsUser `
    /RL LIMITED `
    /F | Out-Null
} catch {
  $taskErrors += "ONLOGON"
}

if ($taskErrors.Count -gt 0) {
  New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
  "@echo off`r`npowershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`"`r`n" | Set-Content -Path $startupCmd -Encoding ASCII
  Write-Output "Scheduled task registration failed for: $($taskErrors -join ', '). Startup fallback created: $startupCmd"
} else {
  Write-Output "Scheduled tasks installed: $taskNameBoot, $taskNameLogon"
}
