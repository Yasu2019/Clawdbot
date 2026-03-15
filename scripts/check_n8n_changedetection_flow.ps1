$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\n8n_changedetection_flow"
$statusPath = Join-Path $stateDir "harness_status.json"
$configPath = Join-Path $stateDir "config.json"

$result = [ordered]@{
  status = $(if (Test-Path $statusPath) { Get-Content -Raw $statusPath | ConvertFrom-Json } else { $null })
  config = $(if (Test-Path $configPath) { Get-Content -Raw $configPath | ConvertFrom-Json } else { $null })
}

$result | ConvertTo-Json -Depth 10
