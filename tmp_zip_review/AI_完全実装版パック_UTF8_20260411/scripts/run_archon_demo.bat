@echo off
setlocal
cd /d %~dp0\..
python app\archon_harness.py
python app\hermes_learning_loop.py
echo Done.
pause
