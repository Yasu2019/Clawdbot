$ErrorActionPreference = "Stop"

Write-Host "Step 1: Git backup"
powershell -ExecutionPolicy Bypass -File .\scripts\git_safe_backup.ps1

Write-Host "Step 2: Standalone build and start"
docker compose -f docker-compose.julia-worker.standalone.yml up -d --build

Write-Host "Step 3: Health check"
Start-Sleep -Seconds 5
Invoke-RestMethod http://localhost:8096/health
Invoke-RestMethod http://localhost:8097/health

Write-Host "Julia Numerical Worker standalone start completed."
