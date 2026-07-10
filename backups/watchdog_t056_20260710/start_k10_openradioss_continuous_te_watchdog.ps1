#Requires -Version 5.1
<#
.SYNOPSIS
  K10 local OpenRadioss (press_blanking) continuous T&E with 3D VTK video to Telegram.
#>
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_openradioss_continuous_te_loop.py"

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_openradioss_continuous_te_loop.py*"
}
if ($existing) {
    Write-Output "K10 OpenRadioss TE loop already running pid=$($existing.ProcessId)"
    exit 0
}

$env:CAE_PARAVIEW_TELEGRAM = "0"
$env:CAE_OPENRADIOSS_VIDEO_TELEGRAM = "1"
Start-Process -FilePath "python" -ArgumentList "`"$scriptPath`" --poll-seconds 300 --timeout 900" -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "K10 OpenRadioss TE loop started (poll 300s)"
