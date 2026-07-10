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
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "global_web_knowledge_harvest_watchdog already running pid=$($existing[0].ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

Start-Process -FilePath $py -ArgumentList "`"$watchdog`" --poll-hours 6" -WorkingDirectory $RepoRoot -WindowStyle Hidden
Write-Output "[OK] Started global_web_knowledge_harvest_watchdog"
