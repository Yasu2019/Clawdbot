param(
    [switch]$ExecuteTrial,
    [int]$IntervalMinutes = 30
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root 'scripts\moldflow_continuous_improvement_supervisor.py'
$python = (Get-Command python.exe).Source
$taskName = 'ClawstackMoldflowContinuousImprovement'
$trialArg = if ($ExecuteTrial) { ' --execute-trial' } else { '' }
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"$trialArg" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description 'Safe Moldflow commercial-reference improvement supervisor; observation by default, bounded trials only with -ExecuteTrial.' -Force | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
