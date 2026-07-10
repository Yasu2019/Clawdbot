#Requires -Version 5.1
<#
.SYNOPSIS
  Keep K10 -> ThinkPad connectivity probes running (5 min default) for RCA.
#>
[CmdletBinding()]
param(
    [int]$IntervalSec = 300
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_thinkpad_connectivity_watch.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_thinkpad_connectivity_watch.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "ThinkPad connectivity watch already running pid=$($existing.ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

$argsLine = "`"$scriptPath`" --daemon --interval-sec $IntervalSec"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "ThinkPad connectivity watch started interval=${IntervalSec}s"
