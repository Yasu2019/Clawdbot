param(
    [int]$KeepStorageGB = 50,
    [int]$OlderThanHours = 168
)

$ErrorActionPreference = "Stop"
$socket = "unix:///var/run/docker-native.sock"
$activeCae = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "k10_tri_track_cae_orchestrator|starter_win64|engine_win64|OpenRadioss"
}
if ($activeCae) {
    Write-Output "Deferred: active CAE process found."
    exit 3
}

$active = (& wsl -d Ubuntu -u root -- systemctl is-active docker-native 2>&1 | Out-String).Trim()
if ($active -ne "active") {
    Write-Output "Deferred: docker-native is not active."
    exit 4
}

& wsl -d Ubuntu -u root -- docker -H $socket builder prune -f `
    --filter "until=${OlderThanHours}h" --keep-storage "${KeepStorageGB}GB"
if ($LASTEXITCODE -ne 0) {
    throw "Native Docker build-cache prune failed."
}
& wsl -d Ubuntu -u root -- docker -H $socket image prune -f `
    --filter "until=${OlderThanHours}h"
if ($LASTEXITCODE -ne 0) {
    throw "Native Docker dangling-image prune failed."
}
Write-Output "Safe GC complete; volumes and containers were not pruned."
