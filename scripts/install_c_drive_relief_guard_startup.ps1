$ErrorActionPreference = 'Stop'

$startupDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup'
$cmdPath = Join-Path $startupDir 'ClawdbotCDriveReliefGuard.cmd'
$psPath = 'D:\Clawdbot_Docker_20260125\scripts\start_c_drive_relief_guard.ps1'
$content = "@echo off`r`npowershell -ExecutionPolicy Bypass -File `"$psPath`"`r`n"
[System.IO.File]::WriteAllText($cmdPath, $content, [System.Text.Encoding]::ASCII)
Write-Output $cmdPath
