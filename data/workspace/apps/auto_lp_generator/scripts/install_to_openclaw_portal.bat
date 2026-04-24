@echo off
set TARGET=D:\Clawdbot_Docker_20260125\clawstack_v2\portal\apps\auto_lp_generator
echo Installing Portal card to:
echo %TARGET%
xcopy /E /I /Y portal\apps\auto_lp_generator "%TARGET%"
echo Done.
pause
