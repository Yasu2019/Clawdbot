[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toggleScript = Join-Path $PSScriptRoot "toggle_docker_desktop_quiet_mode.ps1"

$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    quietMode = $false
    error = $null
}

try {
    & powershell -ExecutionPolicy Bypass -File $toggleScript -Mode off | Out-Null
}
catch {
    $result.error = $_.Exception.Message
}

$result | ConvertTo-Json -Depth 4
