@echo off
chcp 65001 >nul
REM register stagnant_walk_watchdog task (every 6 hours). ASCII comments only.
REM 2026-07-30 user-approved: periodically check motion_learning_supervisor.py
REM autonomous runs (e.g. --skill walk_auto) and safely stop unproductive ones
REM (3+ consecutive cycles with min_upright < 0.02). See:
REM projects\AtsugiMechaCity\rl_integration\autonomy\stagnant_walk_watchdog.py
set ROOT=D:\Clawdbot_Docker_20260125
schtasks /Create /F /TN "Clawstack\StagnantWalkWatchdog" /SC HOURLY /MO 6 ^
  /TR "cmd /c cd /d %ROOT% && set PYTHONIOENCODING=utf-8 && python projects\AtsugiMechaCity\rl_integration\autonomy\stagnant_walk_watchdog.py >> data\workspace\apps\mecha_motion_lab\stagnant_walk_watchdog_task.log 2>&1"
echo done. run once now:
cd /d %ROOT%
set PYTHONIOENCODING=utf-8
python projects\AtsugiMechaCity\rl_integration\autonomy\stagnant_walk_watchdog.py
pause
