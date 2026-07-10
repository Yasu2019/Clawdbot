#Requires -Version 5.1
<#
.SYNOPSIS
  Keep fleet_revolutionary_evolution_loop.py running (24/365 rollup + DOE + recovery).
#>
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\fleet_revolutionary_evolution_loop.py"
$venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pyExe = if (Test-Path $venvPy) { $venvPy } else { "python" }

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*fleet_revolutionary_evolution_loop.py*"
}
if ($existing) {
    Write-Output "Fleet revolutionary evolution loop already running pid=$($existing.ProcessId)"
    exit 0
}

Start-Process -FilePath $pyExe -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "Fleet revolutionary evolution loop started"
