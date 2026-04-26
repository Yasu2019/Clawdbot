$ErrorActionPreference = 'Stop'

$python = 'python'
$script = 'D:\Clawdbot_Docker_20260125\data\workspace\c_drive_relief_guard.py'
$logDir = 'E:\ClawstackData\logs'
$stdoutPath = Join-Path $logDir 'c_drive_relief_guard.out.log'
$stderrPath = Join-Path $logDir 'c_drive_relief_guard.err.log'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -like '*c_drive_relief_guard.py*'
}
if ($existing) {
    Write-Output "already_running"
    exit 0
}

Start-Process -FilePath $python `
    -ArgumentList @($script, '--warn-gb', '60', '--critical-gb', '30', '--days-old', '2', '--poll-seconds', '600') `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden

Write-Output "started"
