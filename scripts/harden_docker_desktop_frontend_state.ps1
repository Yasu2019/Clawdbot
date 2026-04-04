[CmdletBinding()]
param(
    [string]$ProjectRoot = "D:\Clawdbot_Docker_20260125"
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
    param([string]$Path)
    Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-JsonFile {
    param(
        [string]$Path,
        [Parameter(Mandatory = $true)]$Object
    )
    $Object | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$statusPath = Join-Path $ProjectRoot "data\workspace\docker_desktop_frontend_hardening_status_$timestamp.json"
$backupRoot = Join-Path $ProjectRoot "backups\docker_desktop_frontend_hardening\$timestamp"
$persistedStatePath = Join-Path $env:APPDATA "Docker Desktop\persisted-state.json"

$status = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    persistedStatePath = $persistedStatePath
    backupRoot = $backupRoot
    hiddenRoutes = @()
    dockerAiSuggestionDisabled = $false
    error = $null
}

try {
    if (-not (Test-Path $persistedStatePath)) {
        throw "persisted-state.json not found: $persistedStatePath"
    }

    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    Copy-Item -LiteralPath $persistedStatePath -Destination (Join-Path $backupRoot "persisted-state.json") -Force

    $persisted = Read-JsonFile -Path $persistedStatePath
    if ($persisted.PSObject.Properties.Name -contains "dockerAI.showSuggestion") {
        $persisted.'dockerAI.showSuggestion' = $false
        $status.dockerAiSuggestionDisabled = $true
    }

    $routesToHide = @("dockerAgent", "models", "mcp", "dockerHub", "dockerScout")
    $dashboardRoutes = $persisted.'sideNavBar.dashboardRoutes'
    if ($dashboardRoutes) {
        foreach ($entry in $dashboardRoutes) {
            if ($entry.Count -ge 2) {
                $routeKey = [string]$entry[0]
                $routeValue = $entry[1]
                if ($routesToHide -contains $routeKey) {
                    $routeValue.hiddenByUser = $true
                    $status.hiddenRoutes += $routeKey
                }
            }
        }
    }

    Write-JsonFile -Path $persistedStatePath -Object $persisted
}
catch {
    $status.error = $_.Exception.Message
}
finally {
    $status | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    Write-Output "Status: $statusPath"
    if ($status.error) {
        Write-Error $status.error
    }
}
