$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$runnerFile = Join-Path $repoRoot "data\state\email_enrich\runner.json"
$preStatus = Join-Path $repoRoot "data\state\email_preprocess\harness_status.json"
$enrichStatus = Join-Path $repoRoot "data\state\email_enrich\harness_status.json"

if (Test-Path $runnerFile) {
  Write-Output "Runner:"
  Get-Content -Raw $runnerFile
  Write-Output ""
}

if (Test-Path $preStatus) {
  Write-Output "Preprocess:"
  Get-Content -Raw $preStatus
  Write-Output ""
}

if (Test-Path $enrichStatus) {
  Write-Output "Enrich:"
  Get-Content -Raw $enrichStatus
} else {
  Write-Output "Enrich: missing"
}
