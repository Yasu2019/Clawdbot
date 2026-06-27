# Clawstack V2 Daily Backup Script
# Created by Antigravity (AI) - 2026-04-11

$BackupDir = "D:\ClawstackArchive\DailyBackup"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmm"
$PostgresContainer = "clawstack-unified-postgres-1"
$PaperlessMediaDir = "D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\media"
$N8nDataDir = "D:\Clawdbot_Docker_20260125\clawstack_v2\data\n8n"
$N8nContainer = "clawstack-unified-n8n-1"

Write-Host "Starting Clawstack V2 Infrastructure Backup..." -ForegroundColor Cyan

# 1. Postgres Database Dump
$DbDumpFile = "$BackupDir\postgres_dump_$Timestamp.sql"
Write-Host "Dumping Postgres database..."

# T-WAL-001修正: pg_dump結果を /tmp に書いてからホストにコピー
# 旧実装はPostgreSQLデータディレクトリ(/var/lib/postgresql/data)に直接書き込んでいた(危険)
docker exec $PostgresContainer sh -c "pg_dumpall -U postgres --globals-only > /tmp/temp_dump.sql && pg_dump -U postgres -d postgres >> /tmp/temp_dump.sql && pg_dump -U postgres -d sim_trials >> /tmp/temp_dump.sql"
docker cp "${PostgresContainer}:/tmp/temp_dump.sql" $DbDumpFile
docker exec $PostgresContainer rm -f /tmp/temp_dump.sql

if (Test-Path $DbDumpFile) {
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

# 3. n8n Database & Workflow Backup
Write-Host "Backing up n8n database and workflows..."
$N8nDbFile = "$BackupDir\n8n_database_$Timestamp.sqlite"
Copy-Item "$N8nDataDir\database.sqlite" $N8nDbFile -Force

# Export workflows to JSON
$N8nExportDir = "$BackupDir\n8n_workflows_$Timestamp"
New-Item -ItemType Directory -Force -Path $N8nExportDir | Out-Null
docker exec -u root -e N8N_USER_FOLDER=/root/.n8n $N8nContainer n8n export:workflow --backup --output=/workspace/restore/backups/
# Copy from workspace to backup archive
Copy-Item "D:\Clawdbot_Docker_20260125\data\workspace\restore\backups\*" $N8nExportDir -Force

if ($LASTEXITCODE -eq 0) {
    Write-Host "n8n backup successful." -ForegroundColor Green
} else {
    Write-Host "n8n backup encountered errors during export." -ForegroundColor Yellow
}

# 3. Cleanup Old Backups (Retain last 7 days)
Write-Host "Cleaning up backups older than 7 days..."
Get-ChildItem -Path $BackupDir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force
Write-Host "Cleanup complete."

Write-Host "Backup Process Finished." -ForegroundColor Cyan
