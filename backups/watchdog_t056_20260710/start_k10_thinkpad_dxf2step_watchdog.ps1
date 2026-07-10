#Requires -Version 5.1
<#
.SYNOPSIS
  Keep K10 -> ThinkPad DXF2STEP T&E loop running (native FreeCAD on ThinkPad).
#>
[CmdletBinding()]
param(
    [int]$PollSeconds = 600
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$stopCae = Join-Path $repoRoot "scripts\stop_k10_thinkpad_cae_loop.ps1"
$scriptPath = Join-Path $repoRoot "scripts\k10_thinkpad_dxf2step_loop.py"

if (Test-Path $stopCae) {
    & $stopCae 2>&1 | Out-Host
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_thinkpad_dxf2step_loop.py*"
}
if ($existing) {
    Write-Output "ThinkPad DXF2STEP loop already running pid=$($existing.ProcessId)"
    exit 0
}

$pythonExe = "python"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
}

$argsLine = "`"$scriptPath`" --daemon --poll-seconds $PollSeconds"
$env:DXF2STEP_QUALITY_PREFLIGHT_REQUIRED = "1"
$env:DXF2STEP_QUALITY_LLM_MODE = "always"
$env:DXF2STEP_QUALITY_LLM_MODEL = "openai/gpt-4o"
Start-Process -FilePath $pythonExe -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "ThinkPad DXF2STEP T&E loop started using $pythonExe poll=${PollSeconds}s"
