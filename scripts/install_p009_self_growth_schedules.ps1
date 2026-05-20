param(
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
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
    [string]$Description
  )

  $action = New-PowerShellAction -ScriptPath $ScriptPath
  $startup = New-ScheduledTaskTrigger -AtStartup
  $loop = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval $Interval -RepetitionDuration (New-TimeSpan -Days 3650)
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($startup, $loop) -Settings $settings -Description $Description -Force | Out-Null
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
  }
)

$registered = @()
$fallback = $false
foreach ($task in $tasks) {
  try {
    if ($task.python) {
      $scriptPath = [string]$task.script
      $action = New-ScheduledTaskAction -Execute "python" -Argument "`"$scriptPath`""
      $startup = New-ScheduledTaskTrigger -AtStartup
      $loop = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval $task.interval -RepetitionDuration (New-TimeSpan -Days 3650)
      $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
      Register-ScheduledTask -TaskName $task.name -Action $action -Trigger @($startup, $loop) -Settings $settings -Description $task.description -Force | Out-Null
    } else {
      Register-LoopTask -TaskName $task.name -ScriptPath $task.script -Interval $task.interval -Description $task.description
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
