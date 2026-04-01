$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\continuous_system_improvement.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match "python" -and $_.CommandLine -like "*continuous_system_improvement.py*"
}
if ($existing) {
  Write-Output "Continuous system improvement patrol already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --poll-seconds 600" -WindowStyle Hidden
Write-Output "Continuous system improvement patrol started."
