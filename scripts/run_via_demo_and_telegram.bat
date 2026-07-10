@echo off
chcp 65001 >nul
REM run Visual Inspection AI demo (7 cases) and send results to Telegram. ASCII comments.
set ROOT=D:\Clawdbot_Docker_20260125
cd /d %ROOT%
set PYTHONIOENCODING=utf-8
python projects\visual_inspection_ai\scripts\run_demo_cases.py
python scripts\send_via_demo_telegram.py
pause
