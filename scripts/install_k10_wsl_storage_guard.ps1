param(
    [string]$Repository = "D:\Clawdbot_Docker_20260125"
)

$ErrorActionPreference = "Stop"
$python = Join-Path $Repository ".venv\Scripts\python.exe"
$guard = Join-Path $Repository "scripts\k10_wsl_storage_guard.py"
$argument = "`"$guard`" --json --task-mode"
$action = New-ScheduledTaskAction -Execute $python -Argument $argument -WorkingDirectory $Repository
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "K10 WSL Storage Guard" -Action $action -Trigger $trigger `
    -Settings $settings -Description "Monitor E/F and WSL/Docker VHD capacity; gate new CAE dispatch." `
    -Force | Out-Null
Write-Output "Installed scheduled task: K10 WSL Storage Guard"

$gcScript = Join-Path $Repository "scripts\k10_native_docker_safe_gc.ps1"
$gcAction = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$gcScript`""
$gcTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "03:30"
$gcSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "K10 Native Docker Safe GC" -Action $gcAction -Trigger $gcTrigger `
    -Settings $gcSettings -Description "Prune old native Docker build cache and dangling images only." `
    -Force | Out-Null
Write-Output "Installed scheduled task: K10 Native Docker Safe GC"
