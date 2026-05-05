# OpenClaw/Clawstack Blender Motion Pipeline 事前確認
Write-Host "=== Path ==="
Get-Location
Write-Host "=== Docker ==="
docker ps -a
Write-Host "=== Compose ==="
docker compose ps
Write-Host "=== Ports ==="
netstat -ano | findstr ":8081"
netstat -ano | findstr ":8083"
netstat -ano | findstr ":6333"
netstat -ano | findstr ":9000"
netstat -ano | findstr ":11434"
Write-Host "=== Blender ==="
where.exe blender
blender --version
Write-Host "=== Python ==="
python --version
pip --version
