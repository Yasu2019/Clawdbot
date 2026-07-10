@echo off
chcp 65001 >nul
REM ============================================================
REM Moldflow CAE Studio API 再起動 (STEP2/3 発効用)
REM 作成: Fable5 2026-07-10 / 引継ぎ: docs\handover\MOLDFLOW_STUDIO_REFACTOR_STEP2_20260710.md
REM ============================================================
set ROOT=D:\Clawdbot_Docker_20260125
set APPDIR=%ROOT%\data\workspace\apps\moldflow_cae_studio
set PIDFILE=%APPDIR%\api.pid

if exist "%PIDFILE%" (
  set /p OLDPID=<"%PIDFILE%"
  echo [1/3] 旧APIプロセス %OLDPID% を停止...
  taskkill /PID %OLDPID% /F >nul 2>&1
  timeout /t 2 /nobreak >nul
)

echo [2/3] 新API起動 (port 8776, PYTHONIOENCODING=utf-8)...
cd /d %ROOT%
powershell -NoProfile -Command "$env:PYTHONIOENCODING='utf-8'; $p = Start-Process python -ArgumentList 'scripts\moldflow_cae_studio_api.py' -WorkingDirectory '%ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%APPDIR%\api.out.log' -RedirectStandardError '%APPDIR%\api.err.log' -PassThru; Set-Content -Path '%PIDFILE%' -Value $p.Id -Encoding ascii; Write-Host ('  new pid: ' + $p.Id)"

echo [3/3] ヘルスチェック...
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8776/api/health
echo.
echo 上に {"ok": true, ...} が出れば再起動成功。maturityパネル確認: ブラウザでindex.htmlをリロード
pause
