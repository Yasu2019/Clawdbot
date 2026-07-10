#Requires -Version 5.1
<#
.SYNOPSIS
  K10 tri-track CAE: OpenFOAM@lavie + OpenRadioss@red_lavie + FEM Impact@thinkpad (continuous).
#>
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "scripts\k10_tri_track_cae_orchestrator.py"

$existing = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like "python*" -and $_.CommandLine -like "*k10_tri_track_cae_orchestrator.py*"
})
# T051既知欠陥の修正(2026-07-10): 2重起動を検知したら全停止して単一起動し直す。
# -Restart 指定時は単一稼働でも再起動(設定yaml再読込用)。
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $args -contains "-Restart")) {
    Write-Output "Stopping $($existing.Count) orchestrator instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
} elseif ($existing.Count -eq 1) {
    Write-Output "Tri-track CAE orchestrator already running pid=$($existing.ProcessId) (restart: add -Restart)"
    exit 0
}

$env:CAE_PARAVIEW_VIDEO_TELEGRAM = "1"
# Legacy cae_te_engine path (keep enabled for unified delivery)
$env:CAE_PARAVIEW_TELEGRAM = "1"
$venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
$deployScript = Join-Path $repoRoot "scripts\k10_thinkpad_fem_impact_deploy.py"
if ((Test-Path $venvPy) -and (Test-Path $deployScript)) {
    $syncJob = Start-Job -ScriptBlock {
        param($py, $script)
        & $py $script --sync-script 2>&1
    } -ArgumentList $venvPy, $deployScript
    $null = Wait-Job $syncJob -Timeout 90
    if ($syncJob.State -eq "Running") { Stop-Job $syncJob -Force }
    Remove-Job $syncJob -Force -ErrorAction SilentlyContinue
    Write-Output "ThinkPad fem_impact PNG scripts sync attempted (90s cap)"
}
$pyExe = if (Test-Path $venvPy) { $venvPy } else { "python" }
Start-Process -FilePath $pyExe -ArgumentList "`"$scriptPath`" --continuous --timeout 10800 --no-sync-impact" -WindowStyle Hidden -WorkingDirectory $repoRoot
Write-Output "K10 tri-track CAE orchestrator started (continuous, timeout=10800s, ThinkPad production-only fem_impact)"
