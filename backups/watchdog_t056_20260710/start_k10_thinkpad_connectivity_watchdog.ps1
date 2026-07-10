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
if ($existing) {
    Write-Output "ThinkPad connectivity watch already running pid=$($existing.ProcessId)"
    exit 0
}

$argsLine = "`"$scriptPath`" --daemon --interval-sec $IntervalSec"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "ThinkPad connectivity watch started interval=${IntervalSec}s"
