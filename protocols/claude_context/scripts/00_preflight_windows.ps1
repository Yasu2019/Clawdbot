Write-Host "=== OpenClaw Claude Context Preflight ==="
$ErrorActionPreference = "Continue"

Write-Host "[1] Docker version"
docker version

Write-Host "[2] Existing containers"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

Write-Host "[3] Check ports"
$ports = @(19530,19091,19000,19001,11434,8088,4000,6333)
foreach ($p in $ports) {
  $r = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
  if ($r) { Write-Host "PORT $($p): USED" } else { Write-Host "PORT $($p): FREE" }
}

Write-Host "[4] Ollama models"
try { ollama list } catch { Write-Host "Native ollama command not found. Docker Ollama may still be available." }

Write-Host "[5] Target folders"
$paths = @("D:\Clawdbot_Docker_20260125", "D:\Clawdbot_Docker_20260125\clawstack_v2")
foreach ($path in $paths) {
  if (Test-Path $path) { Write-Host "OK: $path" } else { Write-Host "MISSING: $path" }
}
