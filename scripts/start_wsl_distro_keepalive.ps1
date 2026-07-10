$scriptPath = Join-Path $PSScriptRoot "..\data\workspace\wsl_distro_keepalive.py"
$resolvedScript = [System.IO.Path]::GetFullPath($scriptPath)

$existing = Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^python' -and $_.CommandLine -like "*wsl_distro_keepalive.py*" }

# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
  Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
  $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
  Write-Output "WSL distro keepalive already running. (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
  exit 0
}

Start-Process python -ArgumentList @($resolvedScript, "--distro", "Ubuntu", "--poll-seconds", "30") -WindowStyle Hidden
Write-Output "WSL distro keepalive started."
