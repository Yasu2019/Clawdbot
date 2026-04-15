# Clawstack V2 Daily Backup Script
# Created by Antigravity (AI) - 2026-04-11

$BackupDir = "D:\ClawstackArchive\DailyBackup"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$PostgresContainer = "clawstack-unified-postgres-1"
$PaperlessMediaDir = "D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\media"

Write-Host "Starting Clawstack V2 Infrastructure Backup..." -ForegroundColor Cyan

# 1. Postgres Database Dump
$DbDumpFile = "$BackupDir\postgres_dump_$Timestamp.sql"
Write-Host "Dumping Postgres database..."
docker exec $PostgresContainer pg_dumpall -U postgres > $DbDumpFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "Postgres dump successful: $DbDumpFile" -ForegroundColor Green
} else {
    Write-Host "Postgres dump FAILED!" -ForegroundColor Red
}

# 2. Paperless Media Backup (Zip)
$MediaZipFile = "$BackupDir\paperless_media_$Timestamp.zip"
Write-Host "Compressing Paperless media ($PaperlessMediaDir)..."
Compress-Archive -Path "$PaperlessMediaDir\*" -DestinationPath $MediaZipFile -Force
if ($LASTEXITCODE -eq 0) {
    Write-Host "Media backup successful: $MediaZipFile" -ForegroundColor Green
} else {
    Write-Host "Media backup FAILED!" -ForegroundColor Red
}

# 3. Cleanup Old Backups (Retain last 7 days)
Write-Host "Cleaning up backups older than 7 days..."
Get-ChildItem -Path $BackupDir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force
Write-Host "Cleanup complete."

Write-Host "Backup Process Finished." -ForegroundColor Cyan
