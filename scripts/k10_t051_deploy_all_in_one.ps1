# T051 all-in-one: orchestrator停止 -> red_lavieペア配布 -> 成功時のみ再起動
# 使い方:  powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\k10_t051_deploy_all_in_one.ps1
$ErrorActionPreference = "Continue"
$Repo = "D:\Clawdbot_Docker_20260125"

Write-Host "[1/3] tri-track orchestrator を停止(全インスタンス)..."
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -like "*k10_tri_track_cae_orchestrator*" } |
    ForEach-Object {
        Write-Host "  kill pid=$($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 3

Write-Host "[2/3] red_lavie へ engine+gates ペア配布..."
$out = & "$Repo\.venv\Scripts\python.exe" "$Repo\scripts\k10_red_lavie_deploy_t051_pair.py" 2>&1 | Out-String
Write-Host $out

if ($out -match "PAIR DEPLOY OK") {
    Write-Host "[3/3] 配布成功 -> orchestrator watchdog を再起動(1インスタンス)..." -ForegroundColor Green
    powershell -ExecutionPolicy Bypass -File "$Repo\scripts\start_k10_tri_track_cae_watchdog.ps1"
    Write-Host "=== DONE: T051 ペア配布完了 + orchestrator 再開 ===" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "=== DEPLOY FAILED: orchestrator は停止のままにします(壊れたgatesで空回りさせないため) ===" -ForegroundColor Red
    Write-Host "対処: red_lavie側でワーカーを再起動してから、このスクリプトをもう一度実行してください:" -ForegroundColor Yellow
    Write-Host '  (red_lavie) Get-CimInstance Win32_Process | ? {$_.CommandLine -like "*job_worker*"} | % { Stop-Process -Id $_.ProcessId -Force }'
    Write-Host '  (red_lavie) schtasks /Run /TN ClawstackRedLavieJobWorker'
    exit 1
}
