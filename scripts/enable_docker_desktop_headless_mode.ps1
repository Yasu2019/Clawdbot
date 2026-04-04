[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$toggleScript = Join-Path $PSScriptRoot "toggle_docker_desktop_quiet_mode.ps1"
$startWatchdogScript = Join-Path $PSScriptRoot "start_docker_desktop_ui_watchdog.ps1"
$stopFrontendScript = Join-Path $PSScriptRoot "stop_docker_desktop_frontend_only.ps1"

$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    quietMode = $true
    watchdogStarted = $false
    stopFrontend = $null
    error = $null
}

try {
    & powershell -ExecutionPolicy Bypass -File $toggleScript -Mode on | Out-Null
    & powershell -ExecutionPolicy Bypass -File $startWatchdogScript | Out-Null
    $result.watchdogStarted = $true
    $stopOutput = & powershell -ExecutionPolicy Bypass -File $stopFrontendScript
    if ($stopOutput) {
        $result.stopFrontend = $stopOutput | ConvertFrom-Json
    }
}
catch {
    $result.error = $_.Exception.Message
}

$result | ConvertTo-Json -Depth 6
