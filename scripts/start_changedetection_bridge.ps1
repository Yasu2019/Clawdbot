$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\changedetection_bridge"
$runnerFile = Join-Path $stateDir "runner.json"
$bridge = Join-Path $repoRoot "scripts\bridge_changedetection_to_vikunja.ps1"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\setup_changedetection_bridge.ps1") | Out-Null
powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\setup_n8n_changedetection_flow.ps1") | Out-Null

$proc = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like "*powershell*" -and $_.CommandLine -like "*bridge_changedetection_to_vikunja.ps1*"
} | Select-Object -First 1

if (-not $proc) {
  $proc = Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-File", $bridge
  ) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
  $state = "started"
} else {
  $state = "already_running"
}

$runner = @{
  pid = $proc.Id
  state = $state
  startedAt = (Get-Date).ToString("o")
  command = "powershell -ExecutionPolicy Bypass -File $bridge"
}
$runner | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $runnerFile
Write-Output ($runner | ConvertTo-Json -Depth 4)
