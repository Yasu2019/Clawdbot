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

$keepalive = Start-Process -FilePath "wsl.exe" `
    -ArgumentList @("-d", "Ubuntu", "-u", "root", "--", "sleep", "300") `
    -WindowStyle Hidden -PassThru
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 36; $attempt++) {
        & wsl -d Ubuntu -u root -- test -S /var/run/docker-native.sock
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 5
    }
    if (-not $ready) {
        Write-Output "Deferred: docker-native socket was not ready within three minutes."
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
}
finally {
    if ($keepalive -and -not $keepalive.HasExited) {
        Stop-Process -Id $keepalive.Id
    }
}
Write-Output "Safe GC complete; volumes and containers were not pruned."
