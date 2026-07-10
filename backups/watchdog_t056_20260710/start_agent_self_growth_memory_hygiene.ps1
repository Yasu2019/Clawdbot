$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "data\workspace\agent_self_growth_memory_hygiene.py"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -like "python*" -and $_.CommandLine -like "*agent_self_growth_memory_hygiene.py*"
}
if ($existing) {
  Write-Output "Agent self-growth memory hygiene already running."
  exit 0
}

Start-Process -FilePath "python3" -ArgumentList "`"$scriptPath`" --max-points 1000 --max-mb 100 --poll-seconds 21600" -WindowStyle Hidden
Write-Output "Agent self-growth memory hygiene started."
