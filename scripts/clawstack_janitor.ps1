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

# 3. Summary
$freedGB = [Math]::Round($totalGmailSize / 1GB, 2)
Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "🧹 Host Cleanup Complete" -ForegroundColor Green
Write-Host "🔥 Space Freed from Gmail Ingest: $freedGB GB" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
