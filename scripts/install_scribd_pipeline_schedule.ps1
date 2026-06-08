# install_scribd_pipeline_schedule.ps1
# Registers the safe Scribd scout/ingestion pipeline to run daily.

$ScriptName = "run_scribd_pipeline.ps1"
$ScriptPath = "D:\Clawdbot_Docker_20260125\scripts\$ScriptName"
$TaskName = "Clawstack_Scribd_Daily_Pipeline"
$WorkingDirectory = "D:\Clawdbot_Docker_20260125"

Write-Host "Registering Windows Task Scheduler task for Scribd Pipeline..." -ForegroundColor Green

# Define the action: Run powershell script
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`"" -WorkingDirectory $WorkingDirectory

# Define the triggers: Daily at 02:00, 04:00, 21:00, and 23:00
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "02:00"
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "04:00"
$Trigger3 = New-ScheduledTaskTrigger -Daily -At "21:00"
$Trigger4 = New-ScheduledTaskTrigger -Daily -At "23:00"

# Define the settings: Run only when user is logged on (Interactive GUI needed for Playwright)
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -WakeToRun

# Register the task
try {
    # Check if task already exists, unregister if so
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Write-Host "Task already exists. Re-registering..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger @($Trigger1, $Trigger2, $Trigger3, $Trigger4) -Settings $Settings -Description "Daily safe Scribd related-source scout and authorized local document ingestion. Downloads and autonomous code edits are opt-in by environment variable."
    Write-Host "[SUCCESS] Successfully registered Windows Task Scheduler task '$TaskName'." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to register task: $_" -ForegroundColor Red
}
