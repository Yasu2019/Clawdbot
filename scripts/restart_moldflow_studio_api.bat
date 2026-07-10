@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
REM ============================================================
REM Moldflow CAE Studio API 再起動 v2
REM 修正(2026-07-10): if内%OLDPID%未展開で旧プロセスをkillできていなかった
REM  → 遅延展開+ポート8776リスナー全掃除方式(孤児プロセス対策=T050教訓)
REM ============================================================
set ROOT=D:\Clawdbot_Docker_20260125
set APPDIR=%ROOT%\data\workspace\apps\moldflow_cae_studio
set PIDFILE=%APPDIR%\api.pid

echo [1/3] ポート8776の既存リスナーを全停止(pidファイル非依存)...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8776 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Write-Host ('  stopping pid ' + $_); Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

echo [2/3] 新API起動 (port 8776, PYTHONIOENCODING=utf-8)...
cd /d %ROOT%
powershell -NoProfile -Command "$env:PYTHONIOENCODING='utf-8'; $p = Start-Process python -ArgumentList 'scripts\moldflow_cae_studio_api.py' -WorkingDirectory '%ROOT%' -WindowStyle Hidden -RedirectStandardOutput '%APPDIR%\api.out.log' -RedirectStandardError '%APPDIR%\api.err.log' -PassThru; Set-Content -Path '%PIDFILE%' -Value $p.Id -Encoding ascii; Write-Host ('  new pid: ' + $p.Id)"

echo [3/3] ヘルスチェック...
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8776/api/health
echo.
echo 上に {"ok": true, ...} が出れば再起動成功。孤児が疑われる場合の確認:
echo   powershell "Get-NetTCPConnection -LocalPort 8776 -State Listen | Select OwningProcess"
pause
