@echo off
chcp 65001 >nul
echo [OpenClaw TACO++] installing AutoOps extension...
cd /d %~dp0\..
python scripts\run_local_demo.py
if errorlevel 1 (
  echo Python demo failed. Please check Python 3.11+.
) else (
  echo Demo OK.
)
echo To start with Docker:
echo docker compose -f docker-compose.yml -f OpenClaw_TACOplusplus_AutoOps_UTF8\docker-compose.taco.yml up -d
pause
