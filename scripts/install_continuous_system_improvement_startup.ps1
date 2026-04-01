$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$taskNameLogon = "ClawdbotContinuousSystemImprovementLogon"
$scriptPath = Join-Path $repoRoot "scripts\start_continuous_system_improvement.ps1"
$runAsUser = $env:USERNAME
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$startupCmd = Join-Path $startupDir "ClawdbotContinuousSystemImprovement.cmd"

$action = "powershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`""
$scheduledTaskOk = $true

try {
  $previousPref = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $createResult = & cmd /c "schtasks /Create /TN `"$taskNameLogon`" /SC ONLOGON /TR `"$action`" /RU `"$runAsUser`" /RL LIMITED /F" 2>&1
  if ($LASTEXITCODE -ne 0) {
    $scheduledTaskOk = $false
  }
} finally {
  $ErrorActionPreference = $previousPref
}

if (-not $scheduledTaskOk) {
  New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
  "@echo off`r`npowershell.exe -ExecutionPolicy Bypass -File `"$scriptPath`"`r`n" | Set-Content -Path $startupCmd -Encoding ASCII
  Write-Output "Scheduled task registration failed. Startup fallback created: $startupCmd"
} else {
  Write-Output "Scheduled task installed: $taskNameLogon"
}
