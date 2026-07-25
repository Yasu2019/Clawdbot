$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "startup_orchestrator_guard.ps1")
if (Test-ClawdbotOrchestratorMode) { Write-OrchestratorSkipMessage "install_paperless_rag_watchdog_startup"; exit 0 }

$repoRoot = Split-Path -Parent $PSScriptRoot
$startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$targetPath = Join-Path $startupDir "ClawdbotPaperlessRagWatchdog.cmd"
$launcher = Join-Path $repoRoot "scripts\start_paperless_rag_watchdog.ps1"

$content = "@echo off`r`n"
$content += "powershell -NoProfile -ExecutionPolicy Bypass -File `"$launcher`"`r`n"

Set-Content -LiteralPath $targetPath -Value $content -Encoding ASCII
Write-Output "Created startup launcher: $targetPath"
