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
if ($existing) {
    Write-Output "IATF video light loop already running pid=$($existing.ProcessId)"
    exit 0
}

$argsLine = "`"$scriptPath`" --interval-hours $IntervalHours"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "IATF video light loop started interval=${IntervalHours}h"
