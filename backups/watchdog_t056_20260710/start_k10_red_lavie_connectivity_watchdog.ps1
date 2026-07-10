#Requires -Version 5.1
<#
.SYNOPSIS
  Keep K10 -> Red LAVIE connectivity probes running (5 min default) for RCA.
#>
[CmdletBinding()]
param(
    [int]$IntervalSec = 300
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_red_lavie_connectivity_watch.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_red_lavie_connectivity_watch.py*"
}
if ($existing) {
    Write-Output "Red LAVIE connectivity watch already running pid=$($existing.ProcessId)"
    exit 0
}

$argsLine = "`"$scriptPath`" --daemon --interval-sec $IntervalSec"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "Red LAVIE connectivity watch started interval=${IntervalSec}s"
