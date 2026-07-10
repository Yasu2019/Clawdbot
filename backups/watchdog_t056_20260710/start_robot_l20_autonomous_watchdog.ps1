$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\apps\motion_lab\05_quality_check\robot_l20_autonomous_watchdog.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*robot_l20_autonomous_watchdog.py*"
}
if ($existing) {
    Write-Output "[OK] Robot L20 watchdog already running: PID=$($existing[0].ProcessId)"
    exit 0
}

Start-Process -FilePath "python" -ArgumentList "`"$scriptPath`" --poll-seconds 300" -WorkingDirectory $repoRoot -WindowStyle Hidden
Write-Output "[OK] Robot L20 watchdog started (poll 300s)."
