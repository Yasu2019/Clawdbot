param(
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Task Scheduler does not resolve "python" via PATH (-> 0x80070002). Use the full path.
$PythonExe = "python"
try { $PythonExe = (Get-Command python -ErrorAction Stop).Source } catch {}
$StatusDir = Join-Path $Root "data\state\p009_self_growth_scheduler"
$StatusPath = Join-Path $StatusDir "scheduler_status.json"
New-Item -ItemType Directory -Force -Path $StatusDir | Out-Null

function New-PowerShellAction {
  param([string]$ScriptPath)
  $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
  return New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
}

function Register-LoopTask {
  param(
    [string]$TaskName,
    [string]$ScriptPath,
    [TimeSpan]$Interval,
    [string]$Description,
    [switch]$Interactive
  )

  $action = New-PowerShellAction -ScriptPath $ScriptPath
  $startup = New-ScheduledTaskTrigger -AtStartup
  $loop = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval $Interval -RepetitionDuration (New-TimeSpan -Days 3650)
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
  if ($Interactive) {
    # 2026-07-19 escalation review: GPU学習(CUDA/OpenGL)はデフォルトのS4U(非対話)セッションでは
    # ドライバに届かず失敗する(cudaGetDeviceCount Error 1 + OpenGL GDIフォールバック)。
    # 対話ログオンセッションで実行する(ユーザーログオン中のみ動作)。
    $principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($startup, $loop) -Settings $settings -Principal $principal -Description $Description -Force | Out-Null
  } else {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($startup, $loop) -Settings $settings -Description $Description -Force | Out-Null
  }
}

$tasks = @(
  @{
    name = "Clawstack_P009_Api_Cost_Report"
    script = Join-Path $Root "scripts\run_api_cost_report.ps1"
    interval = New-TimeSpan -Hours 6
    description = "P009 API cost report. Runs at startup and every 6 hours."
  },
  @{
    name = "Clawstack_Agent_Self_Growth_Hygiene"
    script = Join-Path $Root "scripts\start_agent_self_growth_memory_hygiene.ps1"
    interval = New-TimeSpan -Hours 6
    description = "Keeps agent_self_growth_memory hygiene alive."
  },
  @{
    name = "Clawstack_PDCA_Feedback_Refresh"
    script = Join-Path $Root "scripts\run_pdca_feedback_refresh.ps1"
    interval = New-TimeSpan -Hours 1
    description = "Refreshes PDCA scoring and self-growth status."
  },
  @{
    name = "Clawstack_AutoRepair_Allowed"
    script = Join-Path $Root "data\workspace\auto_repair_allowed.py"
    interval = New-TimeSpan -Minutes 30
    description = "Runs bounded auto-repair rules, including P009 and self-growth freshness."
    python = $true
  },
  @{
    name = "Clawstack_MeaningGate_AutoImprover"
    script = Join-Path $Root "scripts\meaning_gate_auto_improver.py"
    interval = New-TimeSpan -Minutes 10
    description = "P025 rev: LLM-driven cause analysis + bounded param fix + auto restart on meaning-gate stops (local LLM -> deepseek-v4-pro escalation)."
    python = $true
  },
  @{
    name = "Clawstack_N8N_Workflow_Watchdog"
    script = Join-Path $Root "scripts\n8n_workflow_watchdog.py"
    interval = New-TimeSpan -Minutes 30
    description = "Detects deactivated n8n workflows, investigates cause, auto-reactivates, notifies Telegram (LLM analysis after 3 consecutive failures)."
    python = $true
  },
  @{
    name = "Clawstack_Content_Proposal_Loop"
    script = Join-Path $Root "scripts\k10_content_proposal_loop.py"
    pyargs = "--once"
    interval = New-TimeSpan -Hours 6
    description = "Notes/Kindle/video topic proposals from scout + north star (was daemon, died 2026-07-14; now scheduler-managed)."
    python = $true
  },
  @{
    name = "Clawstack_Publishing_Updates_Monitor"
    script = Join-Path $Root "scripts\monitor_publishing_updates.py"
    pyargs = "--once"
    interval = New-TimeSpan -Hours 6
    description = "Reflects content catalog changes to Kindle/note/BOOTH etc. channels (scheduler-managed)."
    python = $true
  },
  @{
    name = "Clawstack_Curriculum_Evolution"
    script = Join-Path $Root "scripts\curriculum_evolution_loop.py"
    interval = New-TimeSpan -Hours 6
    description = "Turns all apps/systems into teaching materials, drafts updates with local LLM when sources change (Claude reviews at 04:05)."
    python = $true
  },
  @{
    name = "Clawstack_Motion_Learning_Supervisor"
    script = Join-Path $Root "scripts\start_motion_learning_supervisor.ps1"
    interval = New-TimeSpan -Hours 1
    description = "T066: real RL learning (genesis venv, playbook-driven). Hourly liveness check, restarts only if dead. Interactive session required for GPU (2026-07-19)."
    interactive = $true
  },
  @{
    name = "Clawstack_Recovery_To_Beads"
    script = Join-Path $Root "scripts\recovery_knowledge_to_beads.py"
    interval = New-TimeSpan -Hours 6
    description = "Accumulates all recovery/improvement events (success and failure) into Beads via bd remember."
    python = $true
  }
)

# 全アプリ起動状況レポート: 毎日 0/3/6/9/12/15/18/21 時 (2026-07-19 ユーザー指示)
try {
  $statusScript = Join-Path $Root "scripts\all_apps_status_telegram_report.py"
  $statusAction = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$statusScript`""
  $statusTriggers = @()
  foreach ($h in @(0, 3, 6, 9, 12, 15, 18, 21)) {
    $statusTriggers += New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($h))
  }
  $statusSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName "Clawstack_AllApps_Status_Report" -Action $statusAction -Trigger $statusTriggers -Settings $statusSettings -Description "All apps/nodes status report to Telegram every 3 hours." -Force | Out-Null
  Write-Output "Registered: Clawstack_AllApps_Status_Report (0/3/6/9/12/15/18/21 JST)"
} catch {
  Write-Output "WARN: Clawstack_AllApps_Status_Report registration failed: $_"
}

$registered = @()
$fallback = $false
foreach ($task in $tasks) {
  try {
    if ($task.python) {
      $scriptPath = [string]$task.script
      $argLine = "`"$scriptPath`""
      if ($task.pyargs) { $argLine = "$argLine $($task.pyargs)" }
      $action = New-ScheduledTaskAction -Execute $PythonExe -Argument $argLine
      $startup = New-ScheduledTaskTrigger -AtStartup
      $loop = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval $task.interval -RepetitionDuration (New-TimeSpan -Days 3650)
      $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
      Register-ScheduledTask -TaskName $task.name -Action $action -Trigger @($startup, $loop) -Settings $settings -Description $task.description -Force | Out-Null
    } else {
      Register-LoopTask -TaskName $task.name -ScriptPath $task.script -Interval $task.interval -Description $task.description -Interactive:([bool]$task.interactive)
    }
    $registered += $task.name
  } catch {
    $fallback = $true
    break
  }
}

if ($fallback) {
  $watchdog = Join-Path $Root "scripts\start_p009_self_growth_watchdog.ps1"
  & $watchdog
  $registered += "fallback:p009_self_growth_watchdog"
}

if ($RunNow) {
  foreach ($name in $registered) {
    if ($name -notlike "fallback:*") {
      Start-ScheduledTask -TaskName $name
    }
  }
}

$payload = [ordered]@{
  updatedAt = (Get-Date).ToString("s")
  registered = $registered
  runNow = [bool]$RunNow
  fallback = $fallback
}
$payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $StatusPath -Encoding UTF8
Write-Output "Registered P009/self-growth scheduled tasks: $($registered -join ', ')"
