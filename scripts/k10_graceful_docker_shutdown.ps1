#Requires -Version 5.1
<#
.SYNOPSIS
  Windows シャットダウン/再起動時に PostgreSQL を含む Docker コンテナを
  gracefully に停止する。

  【背景 T-WAL-001 / 2026-06-27】
  Docker のデフォルト stop_grace_period=10秒 では PostgreSQL が checkpoint を
  書き終える前に SIGKILL され WAL 破損が繰り返し発生した。
  このスクリプトを Windows Shutdown イベント(タスクスケジューラ)で実行することで
  Windows が実際に落ちる前に Docker を先に安全停止する。

  登録方法:
    powershell -ExecutionPolicy Bypass -File scripts\k10_graceful_docker_shutdown.ps1 -Register
#>
param(
    [switch]$Register,
    [switch]$Unregister
)

$TaskName  = "Clawstack_K10_GracefulDockerShutdown"
$ScriptPath = $PSCommandPath
$RepoRoot   = Split-Path -Parent $PSScriptRoot
$LogFile    = "C:\ProgramData\Clawstack\stability\docker_shutdown.log"

if ($Register) {
    New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null

    # EventTrigger: System/1074 (shutdown initiated by user/process)
    $triggerXml = @"
<EventTrigger>
  <Subscription>
    &lt;QueryList&gt;
      &lt;Query Id="0" Path="System"&gt;
        &lt;Select Path="System"&gt;*[System[Provider[@Name='USER32'] and EventID=1074]]&lt;/Select&gt;
      &lt;/Query&gt;
    &lt;/QueryList&gt;
  </Subscription>
</EventTrigger>
"@
    $action   = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$ScriptPath`""
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    $task = New-ScheduledTask -Action $action -Settings $settings
    Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force -RunLevel Highest `
        -User "SYSTEM" | Out-Null

    # EventTrigger は XML で直接セット（PowerShell Cmdlet では設定不可）
    $sched = New-Object -ComObject Schedule.Service
    $sched.Connect()
    $folder = $sched.GetFolder("\")
    $taskObj = $folder.GetTask($TaskName)
    $taskDef = $taskObj.Definition
    $trigger = $taskDef.Triggers.Create(0)  # 0 = TASK_TRIGGER_EVENT
    $trigger.Subscription = @"
<QueryList>
  <Query Id="0" Path="System">
    <Select Path="System">*[System[Provider[@Name='USER32'] and EventID=1074]]</Select>
  </Query>
</QueryList>
"@
    $trigger.Delay = "PT3S"
    $folder.RegisterTaskDefinition($TaskName, $taskDef, 4, "SYSTEM", $null, 5) | Out-Null

    Write-Host "[OK] Registered: $TaskName (fires on Event ID 1074 = shutdown)"
    return
}

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "[OK] Unregistered: $TaskName"
    return
}

# === 実行本体: Docker graceful stop ===
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
New-Item -ItemType Directory -Force -Path (Split-Path $LogFile) | Out-Null
"$stamp [START] graceful Docker shutdown triggered" | Add-Content $LogFile -Encoding UTF8

try {
    # Docker が動いているか確認
    $dockerInfo = & docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        "$stamp [SKIP] Docker not running" | Add-Content $LogFile -Encoding UTF8
        exit 0
    }

    # PostgreSQL を最優先で先に停止（checkpoint 書かせる）
    "$stamp [STOP] postgres..." | Add-Content $LogFile -Encoding UTF8
    & docker stop --time 55 clawstack-unified-postgres-1 2>&1 | ForEach-Object {
        "$stamp [postgres] $_" | Add-Content $LogFile -Encoding UTF8
    }

    # 残りのコンテナも停止（30秒猶予）
    "$stamp [STOP] all containers..." | Add-Content $LogFile -Encoding UTF8
    Set-Location $RepoRoot
    & docker compose stop --timeout 30 2>&1 | ForEach-Object {
        "$stamp [compose] $_" | Add-Content $LogFile -Encoding UTF8
    }

    "$stamp [DONE] graceful Docker shutdown complete" | Add-Content $LogFile -Encoding UTF8
} catch {
    "$stamp [ERROR] $_" | Add-Content $LogFile -Encoding UTF8
}
