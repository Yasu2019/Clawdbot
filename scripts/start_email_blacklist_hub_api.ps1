$ErrorActionPreference = 'Stop'

$root = 'D:\Clawdbot_Docker_20260125'
$scriptPath = Join-Path $root 'data\workspace\email_blacklist_hub_api.py'
$statusPath = Join-Path $root 'data\workspace\email_blacklist_hub_status.json'
$pidPath = Join-Path $root 'data\workspace\email_blacklist_hub_windows.pid'
$logPath = Join-Path $root 'data\workspace\email_blacklist_hub.log'
$errPath = Join-Path $root 'data\workspace\email_blacklist_hub.err.log'

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}

function Wait-HttpReady {
    param(
        [string[]]$Urls,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        foreach ($url in $Urls) {
            try {
                Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5 | Out-Null
                return $true
            } catch {
                continue
            }
        }
        Start-Sleep -Seconds 2
    }

    return $false
}

Wait-HttpReady -Urls @('http://127.0.0.1:8792/api/stats', 'http://localhost:8792/api/stats') -TimeoutSeconds 45 | Out-Null

if (Test-Path $pidPath) {
    $existingPid = (Get-Content $pidPath -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($existingPid) {
        $proc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $proc.Id -Force
            Start-Sleep -Seconds 1
        }
    }
}

$process = Start-Process -FilePath $python -ArgumentList $scriptPath -PassThru -WindowStyle Hidden -RedirectStandardOutput $logPath -RedirectStandardError $errPath
$process.Id | Set-Content $pidPath -Encoding ascii

$status = [ordered]@{
    updatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss K')
    pid = $process.Id
    url = 'http://127.0.0.1:8791/api/email-blacklist/candidates'
    status = 'started'
    logPath = $logPath
    errPath = $errPath
}
$status | ConvertTo-Json -Depth 4 | Set-Content $statusPath -Encoding utf8

Wait-HttpReady -Urls @('http://127.0.0.1:8791/api/email-blacklist/candidates', 'http://localhost:8791/api/email-blacklist/candidates') -TimeoutSeconds 45 | Out-Null

Write-Output "email_blacklist_hub_api started pid=$($process.Id)"
