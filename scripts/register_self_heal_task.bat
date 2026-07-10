@echo off
chcp 65001 >nul
REM register self-heal loop task (hourly + at boot). ASCII comments only.
set ROOT=D:\Clawdbot_Docker_20260125
schtasks /Create /F /TN "Clawstack\SelfHealLoops" /SC HOURLY /MO 1 ^
  /TR "cmd /c cd /d %ROOT% && set PYTHONIOENCODING=utf-8 && python scripts\self_heal_loops.py >> scripts\register_self_heal_task.log 2>&1"
schtasks /Create /F /TN "Clawstack\SelfHealLoopsBoot" /SC ONSTART ^
  /TR "cmd /c cd /d %ROOT% && set PYTHONIOENCODING=utf-8 && python scripts\self_heal_loops.py >> scripts\register_self_heal_task.log 2>&1"
echo done. run once now:
cd /d %ROOT%
set PYTHONIOENCODING=utf-8
python scripts\self_heal_loops.py
pause
