$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$bridgePath = Join-Path $repoRoot "scripts\telegram_fast_bridge.js"
$stateDir = Join-Path $repoRoot "data\state\telegram_fast"
$pidFile = Join-Path $stateDir "bridge.pid"
$nodeCmd = (Get-Command node -ErrorAction Stop).Source

if (-not $env:TELEGRAM_FAST_MODEL) {
  $env:TELEGRAM_FAST_MODEL = "qwen3:8b"
}
if (-not $env:TELEGRAM_FAST_API_BASE) {
  $env:TELEGRAM_FAST_API_BASE = "http://127.0.0.1:4000/v1"
}
if (-not $env:TELEGRAM_FAST_API_KEY) {
  $env:TELEGRAM_FAST_API_KEY = "none"
}

if (Test-Path $pidFile) {
  try {
    $existingPid = [int](Get-Content $pidFile -Raw)
  } catch {
    $existingPid = 0
  }

  if ($existingPid -gt 0) {
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    # Telegram サーバー側の旧TCP接続が解放されるまで待機（409 Conflict 防止）
    Start-Sleep -Seconds 32
  }

  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $nodeCmd `
  -ArgumentList @($bridgePath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden

Write-Output "telegram_fast_bridge started"
