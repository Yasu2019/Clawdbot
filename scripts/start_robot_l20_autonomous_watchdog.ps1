$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\apps\motion_lab\05_quality_check\robot_l20_autonomous_watchdog.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*robot_l20_autonomous_watchdog.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "[OK] Robot L20 watchdog already running: PID=$($existing[0].ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

Start-Process -FilePath "python" -ArgumentList "`"$scriptPath`" --poll-seconds 300" -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Output "[OK] Robot L20 watchdog started (poll 300s)."
