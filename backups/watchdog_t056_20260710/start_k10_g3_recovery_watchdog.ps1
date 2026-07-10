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
if ($existing) {
    Write-Output "G3 recovery already running"
    exit 0
}

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$stamp] G3 recovery attempt"
    & $pyExe $scriptPath 2>&1 | Out-Host
    Start-Sleep -Seconds 1800
}
