$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$statusDir = Join-Path $repoRoot "data\state\minipc_core"
$statusPath = Join-Path $statusDir "core_status.json"
$logPath = Join-Path $statusDir "core_start.log"

New-Item -ItemType Directory -Force -Path $statusDir | Out-Null

function Write-CoreLog {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -Path $logPath -Value $line -Encoding UTF8
}

# Keep the always-on layer intentionally tiny.
# Heavy services stay on-demand via start_docker_addons.ps1.
$coreServices = @(
  "ollama"
)

Write-CoreLog "Starting core Docker services: $($coreServices -join ', ')"
docker compose -f "$repoRoot/docker-compose.yml" up -d @coreServices
if ($LASTEXITCODE -ne 0) {
  throw "Failed to start core Docker services."
}

Write-CoreLog "Starting Telegram bridge"
& (Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1")
if ($LASTEXITCODE -ne 0) {
  throw "Failed to start Telegram bridge."
}

$status = [ordered]@{
  updatedAt = (Get-Date).ToString("s")
  ok = $true
  coreServices = $coreServices
  telegramBridge = "canonical_js"
  composeFile = (Join-Path $repoRoot "docker-compose.yml")
}

$status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Output "clawstack core started"
