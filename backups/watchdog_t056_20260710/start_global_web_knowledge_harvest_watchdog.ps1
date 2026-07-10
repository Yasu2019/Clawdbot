#Requires -Version 5.1
<#
.SYNOPSIS
  Start global web knowledge harvest watchdog (public API + north star + AI scout).
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "D:\Clawdbot_Docker_20260125"
)

$ErrorActionPreference = "Stop"
$watchdog = Join-Path $RepoRoot "data\workspace\global_web_knowledge_harvest_watchdog.py"
$py = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $py)) { $py = "pythonw" }

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*global_web_knowledge_harvest_watchdog.py*"
}
if ($existing) {
    Write-Output "global_web_knowledge_harvest_watchdog already running pid=$($existing[0].ProcessId)"
    exit 0
}

Start-Process -FilePath $py -ArgumentList "`"$watchdog`" --poll-hours 6" -WorkingDirectory $RepoRoot -WindowStyle Hidden
Write-Output "[OK] Started global_web_knowledge_harvest_watchdog"
