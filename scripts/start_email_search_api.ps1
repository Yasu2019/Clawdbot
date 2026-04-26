$ErrorActionPreference = 'Stop'

$root = 'D:\Clawdbot_Docker_20260125'
$scriptPath = Join-Path $root 'data\workspace\email_search_api.py'
$pidPath = Join-Path $root 'data\workspace\email_search_api_windows.pid'
$logPath = Join-Path $root 'data\workspace\email_search_api.log'
$errPath = Join-Path $root 'data\workspace\email_search_api.err.log'
$healthUrl = 'http://127.0.0.1:8792/api/stats'

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*email_search_api.py*' } |
  ForEach-Object {
    try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {}
  }

if (Test-Path $pidPath) {
    Remove-Item $pidPath -Force -ErrorAction SilentlyContinue
}

$process = Start-Process -FilePath $python -ArgumentList $scriptPath -PassThru -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError $errPath
$process.Id | Set-Content $pidPath -Encoding ascii

Start-Sleep -Seconds 2

try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 10
    if ($resp.StatusCode -ne 200) {
        throw "Unexpected status code: $($resp.StatusCode)"
    }
} catch {
    throw "email_search_api failed health check: $($_.Exception.Message)"
}

Write-Output "email_search_api started pid=$($process.Id)"
