$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\dify_email_harness.py"
$stateDir = Join-Path $repoRoot "data\state\dify_email_harness"
$pidFile = Join-Path $stateDir "harness.pid"
$pythonCmd = (Get-Command python -ErrorAction Stop).Source

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

if (Test-Path $pidFile) {
  try {
    $existingPid = [int](Get-Content $pidFile -Raw)
  } catch {
    $existingPid = 0
  }

  if ($existingPid -gt 0) {
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
  }

  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$proc = Start-Process -FilePath $pythonCmd `
  -ArgumentList @($scriptPath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -PassThru

Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
Write-Output "dify_email_harness started"
