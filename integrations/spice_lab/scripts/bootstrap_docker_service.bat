@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\..\01_docker_ngspice_service"
echo Building and starting OpenClaw SPICE Lab...
docker compose -f docker-compose.ngspice.yml up -d --build
if errorlevel 1 (
  echo Docker起動に失敗しました。
  exit /b 1
)
echo Health check...
powershell -ExecutionPolicy Bypass -Command "Invoke-RestMethod http://127.0.0.1:8765/health | ConvertTo-Json -Depth 5"
endlocal
