[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("on", "off")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigPath = Join-Path $ProjectRoot "data\workspace\docker_desktop_ui_watchdog_config.json"

if (-not (Test-Path $ConfigPath)) {
    throw "Config not found: $ConfigPath"
}

$config = Get-Content -Raw $ConfigPath | ConvertFrom-Json
$config.quietMode = ($Mode -eq "on")
$config | ConvertTo-Json -Depth 6 | Set-Content -Path $ConfigPath -Encoding utf8

[ordered]@{
    updatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    configPath = $ConfigPath
    quietMode = $config.quietMode
} | ConvertTo-Json -Depth 4
