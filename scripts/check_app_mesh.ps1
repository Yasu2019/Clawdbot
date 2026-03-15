$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runnerFile = Join-Path $repoRoot "data\state\app_mesh\runner.json"
$statusFile = Join-Path $repoRoot "data\state\app_mesh\harness_status.json"
$stateFile = Join-Path $repoRoot "data\state\app_mesh\state.json"

if (Test-Path $runnerFile) {
  Write-Output "Runner:"
  Get-Content -Raw $runnerFile
  Write-Output ""
}

if (Test-Path $statusFile) {
  Write-Output "Status:"
  Get-Content -Raw $statusFile
  Write-Output ""
}

if (Test-Path $stateFile) {
  Write-Output "State:"
  Get-Content -Raw $stateFile
} else {
  Write-Output "State: missing"
}
