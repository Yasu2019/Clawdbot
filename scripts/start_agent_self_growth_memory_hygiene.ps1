$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\agent_self_growth_memory_hygiene.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*agent_self_growth_memory_hygiene.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
  Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
  $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
  Write-Output "Agent self-growth memory hygiene already running. (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --max-points 1000 --max-mb 100 --poll-seconds 21600" -WindowStyle Hidden
Write-Output "Agent self-growth memory hygiene started."
