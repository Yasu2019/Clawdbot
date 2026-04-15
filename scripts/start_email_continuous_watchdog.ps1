$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\email_continuous_watchdog.py"

function Wait-HttpReady {
  param(
    [string[]]$Urls,
    [int]$TimeoutSeconds = 60
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

Wait-HttpReady -Urls @('http://127.0.0.1:8792/api/stats', 'http://127.0.0.1:8791/api/email-blacklist/candidates') -TimeoutSeconds 60 | Out-Null

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*email_continuous_watchdog.py*"
}
if ($existing) {
  Write-Output "Email continuous watchdog already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 60 --stale-minutes 15 --notify-cooldown-minutes 30" -WindowStyle Hidden
Write-Output "Email continuous watchdog started."
