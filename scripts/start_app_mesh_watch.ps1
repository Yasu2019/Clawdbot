$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\app_mesh"
$runnerFile = Join-Path $stateDir "runner.json"
$watcher = Join-Path $repoRoot "scripts\watch_app_mesh.ps1"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$proc = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like "*powershell*" -and $_.CommandLine -like "*watch_app_mesh.ps1*"
} | Select-Object -First 1

if (-not $proc) {
  $proc = Start-Process powershell -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-File", $watcher
  ) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru
  $state = "started"
} else {
  $state = "already_running"
}

$runner = @{
  pid = $proc.Id
  state = $state
  startedAt = (Get-Date).ToString("o")
  command = "powershell -ExecutionPolicy Bypass -File $watcher"
}
$runner | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $runnerFile
Write-Output ($runner | ConvertTo-Json -Depth 4)
