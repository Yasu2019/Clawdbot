#Requires -Version 5.1
<#
.SYNOPSIS
  Keep K10->LAVIE continuous CAE trial-and-error loop running (24/365).
#>
[CmdletBinding()]
param(
    [int]$PollSeconds = 180,
    [switch]$AllowOpenfoamReal
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_lavie_continuous_te_loop.py"

# Rules always + DB; LiteLLM enrich only on FAILED/ERROR (not every 180s cycle)
$env:CAE_FAILURE_ANALYSIS_LLM_MODE = "failed"
$env:CAE_FAILURE_ANALYSIS_TIMEOUT_SEC = "30"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_lavie_continuous_te_loop.py*"
}
if ($existing) {
    Write-Output "LAVIE continuous TE loop already running pid=$($existing.ProcessId)"
    exit 0
}

$pythonExe = "python"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
}

$argsLine = "`"$scriptPath`" --poll-seconds $PollSeconds --timeout 1200"
if ($AllowOpenfoamReal) {
    $argsLine += " --allow-openfoam-real"
}
Start-Process -FilePath $pythonExe -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "LAVIE continuous TE loop started using $pythonExe poll=${PollSeconds}s"
