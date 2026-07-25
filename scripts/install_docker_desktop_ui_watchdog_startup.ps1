$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "startup_orchestrator_guard.ps1")
if (Test-ClawdbotOrchestratorMode) { Write-OrchestratorSkipMessage "install_docker_desktop_ui_watchdog_startup"; exit 0 }

$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$cmdPath = Join-Path $startupDir "ClawdbotDockerDesktopUiWatchdog.cmd"
$repoRoot = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $repoRoot "scripts\start_docker_desktop_ui_watchdog.ps1"

$content = @"
@echo off
powershell -ExecutionPolicy Bypass -File "$startScript"
"@

Set-Content -LiteralPath $cmdPath -Value $content -Encoding ASCII
Write-Output "Created startup launcher: $cmdPath"
