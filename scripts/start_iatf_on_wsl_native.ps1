[CmdletBinding()]
param(
    [switch]$Development = $true,
    [switch]$Production = $true
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$iatfRoot = Join-Path $repoRoot "iatf_system"

function Invoke-NativeCompose {
    param(
        [string]$ProjectName,
        [string]$ComposeFile,
        [string[]]$Services
    )

    Write-Host "Starting $ProjectName on WSL native docker..."
    $svcArgs = $Services -join " "
    $script = @"
cd /mnt/d/Clawdbot_Docker_20260125/iatf_system
COMPOSE_PROJECT_NAME=$ProjectName DOCKER_HOST=unix:///var/run/docker-native.sock docker compose -f $ComposeFile up -d $svcArgs
"@
    wsl -d Ubuntu -- bash -lc $script
}

if ($Development) {
    Invoke-NativeCompose -ProjectName "iatf_system_dev" -ComposeFile "docker-compose.yml" -Services @("db", "redis", "web", "sidekiq")
}

if ($Production) {
    Invoke-NativeCompose -ProjectName "iatf_system" -ComposeFile "docker-compose.production.yml" -Services @("db", "redis", "web", "sidekiq")
}
