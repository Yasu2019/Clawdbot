[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$workspace = Join-Path $repoRoot "data\workspace"
$configPath = Join-Path $workspace "docker_runtime_config.json"
$statusPath = Join-Path $workspace "docker_headless_runtime_status.json"
$enableHeadless = Join-Path $PSScriptRoot "enable_docker_desktop_headless_mode.ps1"

$status = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    mode = "wsl"
    distro = "Ubuntu"
    dockerVersion = $null
    composeVersion = $null
    sampleContainers = @()
    headlessFrontend = $null
    error = $null
}

try {
    @'
{
  "mode": "wsl",
  "wslDistro": "Ubuntu"
}
'@ | Set-Content -LiteralPath $configPath -Encoding UTF8

    $status.dockerVersion = (& wsl -d Ubuntu -- docker version --format '{{.Server.Version}}' 2>$null)
    $status.composeVersion = (& wsl -d Ubuntu -- docker compose version 2>$null)
    $status.sampleContainers = @(& wsl -d Ubuntu -- docker ps --format '{{.Names}}' | Select-Object -First 5)
    $headless = & powershell -ExecutionPolicy Bypass -File $enableHeadless
    if ($headless) {
        $status.headlessFrontend = $headless | ConvertFrom-Json
    }
}
catch {
    $status.error = $_.Exception.Message
}

$status | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
$status | ConvertTo-Json -Depth 6
