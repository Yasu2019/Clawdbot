$ErrorActionPreference = 'Stop'

$python = 'python'
$script = 'D:\Clawdbot_Docker_20260125\data\workspace\storage_cleanup_api.py'
$logDir = 'E:\ClawstackData\logs'
$stdoutPath = Join-Path $logDir 'storage_cleanup_api.out.log'
$stderrPath = Join-Path $logDir 'storage_cleanup_api.err.log'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python' -and $_.CommandLine -like '*storage_cleanup_api.py*'
}
if ($existing) {
    Write-Output "already_running"
    exit 0
}

Start-Process -FilePath $python `
    -ArgumentList @($script) `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath `
    -WindowStyle Hidden

Write-Output "started"
