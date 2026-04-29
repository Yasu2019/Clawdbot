$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bridgePath = Join-Path $repoRoot "scripts\telegram_fast_bridge.js"
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$pidFile = Join-Path $stateDir "bridge.pid"
$startupLog = Join-Path $stateDir "startup.log"
$nodeCmd = (Get-Command node -ErrorAction Stop).Source

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-StartupLog {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -Path $startupLog -Value $line -Encoding UTF8
}

function Get-TelegramBridgeProcesses {
  $escapedRepoRoot = [regex]::Escape($repoRoot)
  @(Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine -match $escapedRepoRoot -and
    $_.CommandLine -match 'telegram_fast_bridge'
  } | Select-Object ProcessId, Name, CommandLine)
}

function Stop-TelegramBridgeProcesses {
  $bridgeProcesses = Get-TelegramBridgeProcesses
  foreach ($proc in $bridgeProcesses) {
    if ($proc.ProcessId -eq $PID) { continue }
    Write-StartupLog "Stopping existing Telegram bridge process pid=$($proc.ProcessId) name=$($proc.Name)"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
  }
}

if (-not $env:TELEGRAM_FAST_MODEL) {
  $env:TELEGRAM_FAST_MODEL = "qwen3:8b"
}
if (-not $env:TELEGRAM_FAST_API_BASE) {
  $env:TELEGRAM_FAST_API_BASE = "http://127.0.0.1:4001/v1"
}
if (-not $env:TELEGRAM_FAST_API_KEY) {
  $env:TELEGRAM_FAST_API_KEY = "none"
}
if (-not $env:TELEGRAM_FAST_TIMEOUT_MS) {
  $env:TELEGRAM_FAST_TIMEOUT_MS = "120000"
}

Stop-TelegramBridgeProcesses

if (Test-Path $pidFile) {
  try {
    $existingPid = [int](Get-Content $pidFile -Raw)
  } catch {
    $existingPid = 0
  }

  if ($existingPid -gt 0) {
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    Write-StartupLog "Stopped stale pid from bridge.pid: $existingPid"
  }

  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 3

Start-Process -FilePath $nodeCmd `
  -ArgumentList @($bridgePath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden

Write-StartupLog "Started canonical Telegram bridge via node: $bridgePath"
Write-Output "telegram_fast_bridge started"
