$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\central_patrol_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*central_patrol_watchdog.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
  Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
  $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
  Write-Output "Central Patrol Watchdog already running. (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`"" -WindowStyle Hidden
Write-Output "Central Patrol Watchdog started (High Frequency Patrol)."
