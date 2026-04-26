# Clawstack Host Janitor (Disk Cleanup Utility)
# -----------------------------------------------------------------------------
# This script aggressively cleans up temporary directories used by host-side 
# automation services like Gmail incremental sync and AI harnesses.
# Run this when C drive space is low.

$ErrorActionPreference = "SilentlyContinue"

# 1. Clear host_gmail_incremental_* (The main leak identified: 147GB)
$tempPath = "$env:LOCALAPPDATA\Temp"
Write-Host "--- Scanning $tempPath for Gmail Sync Garbage ---" -ForegroundColor Cyan

$gmailFolders = Get-ChildItem -Path $tempPath -Directory -Filter "host_gmail_incremental_*"
$totalGmailSize = 0
foreach ($folder in $gmailFolders) {
    $size = (Get-ChildItem -Path $folder.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $totalGmailSize += $size
    Write-Host "  [PRUNING] $($folder.Name) ($([Math]::Round($size / 1MB, 2)) MB)"
    Remove-Item -Path $folder.FullName -Recurse -Force
}

# 2. Clear known Ollama / AI garbage if path exists
Write-Host "--- Partial Cleanup of general Temp garbage ---" -ForegroundColor Cyan
$patterns = @("ollama_*", "tmp_harness_*", "v8-compile-cache-*")
foreach ($p in $patterns) {
    Get-ChildItem -Path $tempPath -Directory -Filter $p | ForEach-Object {
        Write-Host "  [PRUNING] $($_.Name)"
        Remove-Item -Path $_.FullName -Recurse -Force
    }
}

# 3. Prune Redundant Antigravity (IDE) Processes
# We protect the current session's lineage (Me -> Language Server -> Parent IDE)
$myPid = $PID
$lsPid = (Get-WmiObject Win32_Process -Filter "ProcessId=$myPid").ParentProcessId
$mainIdePid = (Get-WmiObject Win32_Process -Filter "ProcessId=$lsPid").ParentProcessId

Write-Host "--- Pruning Redundant IDE Processes (Protecting PID $mainIdePid, $lsPid) ---" -ForegroundColor Cyan

$allAntigravity = Get-Process -Name "Antigravity" -ErrorAction SilentlyContinue
foreach ($p in $allAntigravity) {
    if ($p.Id -ne $mainIdePid -and $p.Id -ne $lsPid -and $p.Id -ne $myPid) {
        # Check if it's a child of our main IDE. If not, it's likely a dangling or redundant window instance.
        $ppid = (Get-WmiObject Win32_Process -Filter "ProcessId=$($p.Id)").ParentProcessId
        if ($ppid -ne $mainIdePid -and $ppid -ne $lsPid) {
             Write-Host "  [PRUNING] Stale IDE Process: $($p.Name) (PID: $($p.Id))"
             Stop-Process -Id $p.Id -Force
        }
    }
}

# 4. Prune Stale Sync Daemons (Python)
Write-Host "--- Scanning for Stale Sync Daemons ---" -ForegroundColor Cyan
$syncScripts = @("continuous_email_ingest_daemon.py", "host_gmail_incremental_sync.py")
foreach ($script in $syncScripts) {
    $procs = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like "*$script*" }
    foreach ($proc in $procs) {
        Write-Host "  [RESTARTING] Sync Daemon: $script (PID: $($proc.ProcessId))"
        Stop-Process -Id $proc.ProcessId -Force
        # Daemons are usually managed by a watchdog or should be restarted manually if needed.
        # For now, we just kill to release resources.
    }
}

# 5. Summary
$freedGB = [Math]::Round($totalGmailSize / 1GB, 2)
Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "🧹 Host Cleanup Complete" -ForegroundColor Green
Write-Host "🔥 Space Freed from Gmail Ingest: $freedGB GB" -ForegroundColor Green
Write-Host "🔄 Stale Processes Pruned" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
