#Requires -Version 5.1
<#
.SYNOPSIS
  K10 light IATF video status refresh (default 4h, no heavy render).
#>
[CmdletBinding()]
param([int]$IntervalHours = 4)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_iatf_video_light_loop.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_iatf_video_light_loop.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "IATF video light loop already running pid=$($existing.ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

$argsLine = "`"$scriptPath`" --interval-hours $IntervalHours"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "IATF video light loop started interval=${IntervalHours}h"
