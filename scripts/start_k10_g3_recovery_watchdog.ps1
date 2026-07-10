#Requires -Version 5.1
<#
.SYNOPSIS
  Retry G3 n8n/IATF bringup from K10 when Tailscale recovers (30min default in policy).
#>
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_g3_operations_start.py"
$venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pyExe = if (Test-Path $venvPy) { $venvPy } else { "python" }

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_g3_operations_start.py*"
}
# T056: 多重起動は全掃除して単一化。再読込再起動は WATCHDOG_RESTART=1 で。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Output "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "G3 recovery already running (single instance OK; set WATCHDOG_RESTART=1 to force restart)"
    exit 0
}

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$stamp] G3 recovery attempt"
    & $pyExe $scriptPath 2>&1 | Out-Host
    Start-Sleep -Seconds 1800
}
