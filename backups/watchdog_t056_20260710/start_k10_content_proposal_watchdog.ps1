#Requires -Version 5.1
<#
.SYNOPSIS
  K10 light loop: Notes/Kindle/video topic proposals (default 6h).
#>
[CmdletBinding()]
param([int]$IntervalHours = 6)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_content_proposal_loop.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_content_proposal_loop.py*"
}
if ($existing) {
    Write-Output "Content proposal loop already running pid=$($existing.ProcessId)"
    exit 0
}

$argsLine = "`"$scriptPath`" --interval-hours $IntervalHours"
Start-Process -FilePath "python" -ArgumentList $argsLine -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "Content proposal loop started interval=${IntervalHours}h"
