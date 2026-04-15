# Emergency Stabilization Script (Panic Button)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/panic_stabilize.ps1

Write-Host "--- Emergency Stabilization Started ---" -ForegroundColor Cyan

# 1. Stop non-essential Python processes (excluding critical daemons)
Write-Host "[1/4] Terminating non-essential Python and Node processes..." -ForegroundColor Yellow
$essential_pids = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*watchdog*" -or $_.CommandLine -like "*improvement*" } | Select-Object -ExpandProperty Id
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $essential_pids -notcontains $_.Id } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*language-server*" -or $_.CommandLine -like "*mcp*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Trigger Lite Mode in Docker
Write-Host "[2/4] Enforcing Lite Mode (Stopping heavy Docker services)..." -ForegroundColor Yellow
$optimizer = Join-Path $PSScriptRoot "../data/workspace/minipc_optimizer.py"
python $optimizer apply-lite

# 3. Clear WSL Cache if running
Write-Host "[3/4] Requesting WSL memory release..." -ForegroundColor Yellow
wsl --shutdown -ErrorAction SilentlyContinue

# 4. Clean up temp files
Write-Host "[4/4] Triggering I/O hygiene cleanup..." -ForegroundColor Yellow
python $optimizer cleanup-temp

Write-Host "--- System Stabilized ---" -ForegroundColor Green
Write-Host "Note: WSL will restart automatically when you next use a Docker or WSL command."
