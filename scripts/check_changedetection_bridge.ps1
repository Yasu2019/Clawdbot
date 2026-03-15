$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runnerFile = Join-Path $repoRoot "data\state\changedetection_bridge\runner.json"
$statusFile = Join-Path $repoRoot "data\state\changedetection_bridge\harness_status.json"
$stateFile = Join-Path $repoRoot "data\state\changedetection_bridge\state.json"
$configFile = Join-Path $repoRoot "data\state\changedetection_bridge\config.json"
$n8nFlowConfigFile = Join-Path $repoRoot "data\state\n8n_changedetection_flow\config.json"
$n8nFlowStatusFile = Join-Path $repoRoot "data\state\n8n_changedetection_flow\harness_status.json"

foreach ($item in @(
  @{ Name = "Runner"; Path = $runnerFile },
  @{ Name = "Status"; Path = $statusFile },
  @{ Name = "State"; Path = $stateFile },
  @{ Name = "Config"; Path = $configFile },
  @{ Name = "n8n Flow Status"; Path = $n8nFlowStatusFile },
  @{ Name = "n8n Flow Config"; Path = $n8nFlowConfigFile }
)) {
  if (Test-Path $item.Path) {
    Write-Output "$($item.Name):"
    Get-Content -Raw $item.Path
    Write-Output ""
  }
}
