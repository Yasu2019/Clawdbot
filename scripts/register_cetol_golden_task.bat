@echo off
chcp 65001 >nul
REM register CETOL golden regression daily task (07:40). ASCII comments only.
set ROOT=D:\Clawdbot_Docker_20260125
schtasks /Create /F /TN "Clawstack\CetolGoldenRegression" /SC DAILY /ST 07:40 ^
  /TR "cmd /c cd /d %ROOT% && set PYTHONIOENCODING=utf-8 && python scripts\cetol_golden_regression.py >> scripts\register_cetol_golden_task.log 2>&1"
echo done. run once now:
cd /d %ROOT%
set PYTHONIOENCODING=utf-8
python scripts\cetol_golden_regression.py
pause
