@echo off
set PORT=8010
if not "%AUTO_LP_PORT%"=="" set PORT=%AUTO_LP_PORT%
echo Checking Auto LP Generator on port %PORT% ...
curl http://127.0.0.1:%PORT%/health
echo.
pause
