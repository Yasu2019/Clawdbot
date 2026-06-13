# Run ON Red LAVIE (Admin PowerShell). Downloads bringup from K10 :8123 — no local repo required.
# D:\Clawdbot_Docker_20260125 exists only on K10, not on this machine.
#
# Invoke (ExecutionPolicy Bypass required on Red LAVIE):
#   $K10 = "http://100.119.18.40:8123"
#   Invoke-WebRequest "$K10/red_lavie_bootstrap_from_k10.ps1" -OutFile $env:TEMP\bootstrap.ps1 -UseBasicParsing
#   powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\bootstrap.ps1 -K10 $K10
param(
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$Token = "",
    [string]$InstallRoot = "C:\clawstack_satellite"
)

$ErrorActionPreference = "Stop"

$urls = @(
    "$K10/red_lavie_local_bringup.ps1",
    "$K10/red_lavie_start_job_worker.ps1",
    "$K10/red_lavie_start_monitor.ps1"
)
foreach ($url in $urls) {
    $name = Split-Path $url -Leaf
    $dest = Join-Path $env:TEMP $name
    Write-Host "Download $url -> $dest"
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
}

$bringup = Join-Path $env:TEMP "red_lavie_local_bringup.ps1"
$args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $bringup, "-K10", $K10, "-InstallRoot", $InstallRoot)
if ($Token) { $args += @("-Token", $Token) }
& powershell.exe @args

$mon = Join-Path $env:TEMP "red_lavie_start_monitor.ps1"
if (Test-Path $mon) {
    Write-Host "=== monitor ==="
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $mon -K10 $K10
}
