$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\claudian_watchdog.py"

$existing = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*claudian_watchdog.py*" }
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
  Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
  $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
  Write-Output "Claudian watchdog already running. (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
  exit 0
}

$env:CLAWDBOT_REPO_ROOT = $repoRoot
Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 180 --stale-turn-minutes 2" -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Output "Claudian watchdog started."
