@echo off
chcp 65001 >nul
REM install self-heal pulse: startup folder VBS (no admin needed) + start now. ASCII only.
set ROOT=D:\Clawdbot_Docker_20260125
set VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\clawstack_self_heal_pulse.vbs
(
echo Set sh = CreateObject("WScript.Shell"^)
echo sh.CurrentDirectory = "%ROOT%"
echo sh.Environment("Process"^)("PYTHONIOENCODING"^) = "utf-8"
echo sh.Run "pythonw scripts\self_heal_pulse.py", 0, False
) > "%VBS%"
echo [1/2] startup VBS installed: %VBS%
echo [2/2] starting pulse now...
cd /d %ROOT%
set PYTHONIOENCODING=utf-8
start "" /min pythonw scripts\self_heal_pulse.py
timeout /t 5 /nobreak >nul
if exist data\workspace\self_heal_pulse_status.json (echo pulse status file will appear after first cycle) else (echo starting...)
echo done. verify: type data\workspace\self_heal_pulse_status.json
pause
