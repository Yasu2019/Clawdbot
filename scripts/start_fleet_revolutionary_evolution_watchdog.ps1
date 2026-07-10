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
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "Fleet revolutionary evolution loop already running pid=$($existing.ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

Start-Process -FilePath $pyExe -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "Fleet revolutionary evolution loop started"
