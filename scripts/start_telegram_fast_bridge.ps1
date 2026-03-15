$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bridgePath = Join-Path $repoRoot "scripts\telegram_fast_bridge_v3.ps1"

$existing = Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like "*telegram_fast_bridge_v2.ps1*" -or $_.CommandLine -like "*telegram_fast_bridge_v3.ps1*" }

foreach ($proc in $existing) {
  Stop-Process -Id $proc.ProcessId -Force
}

$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$pidFile = Join-Path $stateDir "bridge.pid"
if (Test-Path $pidFile) {
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath "powershell.exe" `
  -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $bridgePath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden

Write-Output "telegram_fast_bridge started"
