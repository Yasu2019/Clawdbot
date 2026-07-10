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
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
  Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
  $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
  Write-Output "Email continuous watchdog already running. (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 60 --stale-minutes 15 --notify-cooldown-minutes 30" -WindowStyle Hidden
Write-Output "Email continuous watchdog started."
