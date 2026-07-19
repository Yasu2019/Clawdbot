$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\apps\motion_lab\05_quality_check\robot_l20_autonomous_watchdog.py"
$statusPath = Join-Path $repoRoot "data\workspace\apps\growth_dashboard\robot_l20_watchdog_status.json"
$logDir = Join-Path $repoRoot "data\workspace\apps\growth_dashboard"

# 2026-07-19 escalation review: statusがstale(>3h)ならハング中の単一インスタンスでも
# 強制再起動する(従来はガードが exit 0 して自己修復不能だった)。
$forceRestart = ($env:WATCHDOG_RESTART -eq "1")
if (-not $forceRestart -and (Test-Path $statusPath)) {
    try {
        $st = Get-Content $statusPath -Raw | ConvertFrom-Json
        $checked = [datetimeoffset]::Parse($st.checked_at)
        $ageH = ((Get-Date).ToUniversalTime() - $checked.UtcDateTime).TotalHours
        if ($ageH -gt 3) {
            Write-Output "Status stale (${ageH}h old) -> force restart"
            $forceRestart = $true
        }
    } catch {
        Write-Output "WARN: status unreadable -> force restart"
        $forceRestart = $true
    }
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*robot_l20_autonomous_watchdog.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $forceRestart)) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "[OK] Robot L20 watchdog already running: PID=$($existing[0].ProcessId) (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

# T008系: schtasksセッションのPATHにpythonが無い場合がある -> フルパス解決(loop starterと同方式)
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

Start-Process -FilePath $PythonExe -ArgumentList "`"$scriptPath`" --poll-seconds 300" -WorkingDirectory $repoRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir "robot_l20_watchdog_stdout.log") `
    -RedirectStandardError (Join-Path $logDir "robot_l20_watchdog_stderr.log")
Write-Output "[OK] Robot L20 watchdog started (poll 300s, python=$PythonExe)."
