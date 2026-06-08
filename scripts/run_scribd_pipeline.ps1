# run_scribd_pipeline.ps1
# Safe Scribd pipeline:
# 1. Scout related Scribd sources and local inventory
# 2. Optional authorized download from Scribd
# 3. Ingest already-authorized local documents into universal_growth.db
# 4. Optional autonomous code improvement (disabled by default)

$WorkspaceDir = "D:\Clawdbot_Docker_20260125"
Set-Location $WorkspaceDir

$LogFile = "$WorkspaceDir\scribd_pipeline.log"
Start-Transcript -Path $LogFile -Append

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host " Starting Daily Scribd Ingestion & Improvement Pipeline" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Step 1: Scout related sources and current local inventory
Write-Host "`n[STEP 1] Running Safe Scribd Related Source Scout..." -ForegroundColor Yellow
python.exe .\scripts\scribd_related_source_scout.py

# Step 2: Download new documents only when explicitly enabled.
# This avoids bypassing platform controls or collecting unauthorized content.
if ($env:SCRIBD_ENABLE_AUTHORIZED_DOWNLOAD -eq "1") {
    Write-Host "`n[STEP 2] Running authorized Scribd Downloader..." -ForegroundColor Yellow
    python.exe .\scripts\scribd_scraper\scribd_downloader.py
} else {
    Write-Host "`n[STEP 2] Skipping Scribd Downloader. Set SCRIBD_ENABLE_AUTHORIZED_DOWNLOAD=1 for authorized downloads." -ForegroundColor Yellow
}

# Step 3: Extract knowledge and save to DB
Write-Host "`n[STEP 3] Running Knowledge Ingestion..." -ForegroundColor Yellow
python.exe .\scripts\scribd_ingestion.py

# Step 4: Trigger Autonomous Code Improvement only when explicitly enabled.
# The autonomous_coder.py script will:
# - Check DB for new theories
# - Backup current code to Git
# - Apply improvements via LLM
# - Sync to LAVIE satellite worker
if ($env:SCRIBD_ENABLE_AUTONOMOUS_CODER -eq "1") {
    Write-Host "`n[STEP 4] Running Autonomous Code Improvement..." -ForegroundColor Yellow
    python.exe .\scripts\autonomous_coder.py --allow-offline
} else {
    Write-Host "`n[STEP 4] Skipping Autonomous Code Improvement. Set SCRIBD_ENABLE_AUTONOMOUS_CODER=1 to enable." -ForegroundColor Yellow
}

Write-Host "`n=====================================================" -ForegroundColor Cyan
Write-Host " Pipeline Execution Completed" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

Stop-Transcript
