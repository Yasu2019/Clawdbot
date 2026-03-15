$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$statusFile = Join-Path $repoRoot "data\state\email_enrich\harness_status.json"
$stateFile = Join-Path $repoRoot "data\state\email_enrich\state.json"

if (Test-Path $statusFile) {
  Write-Output "Status file:"
  Get-Content -Raw $statusFile
} else {
  Write-Output "Status file: missing"
}

if (Test-Path $stateFile) {
  $processedCount = (Select-String -Path $stateFile -Pattern '^\s+"D:\\\\Clawdbot_Docker_20260125\\\\clawstack_v2\\\\data\\\\paperless\\\\consume\\\\email\\\\.*": ' -Encoding UTF8).Count
  Write-Output ""
  Write-Output "Processed entries:"
  Write-Output $processedCount
} else {
  Write-Output ""
  Write-Output "Processed entries:"
  Write-Output 0
}
