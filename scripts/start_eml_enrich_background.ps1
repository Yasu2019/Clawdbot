$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\email_enrich"
$runnerFile = Join-Path $stateDir "runner.json"
$launcher = Join-Path $repoRoot "scripts\start_eml_enrich_for_paperless.ps1"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$existing = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
  $_.Path -like "*python*" -and $_.CommandLine -like "*eml_enrich_for_paperless.py*"
}
if ($existing) {
  $payload = @{
    pid = $existing[0].Id
    startedAt = (Get-Date).ToString("o")
    command = "python scripts/eml_enrich_for_paperless.py"
    state = "already_running"
  }
  $payload | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $runnerFile
  Write-Output ($payload | ConvertTo-Json -Depth 4)
  exit 0
}

$proc = Start-Process powershell -ArgumentList @(
  "-ExecutionPolicy", "Bypass",
  "-File", $launcher
) -WorkingDirectory $repoRoot -WindowStyle Hidden -PassThru

$runner = @{
  pid = $proc.Id
  startedAt = (Get-Date).ToString("o")
  command = "powershell -ExecutionPolicy Bypass -File $launcher"
  state = "started"
}
$runner | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $runnerFile
Write-Output ($runner | ConvertTo-Json -Depth 4)
