$ErrorActionPreference = "Stop"

$Root = "D:\Clawdbot_Docker_20260125\clawstack_v2"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Backup = Join-Path $Root "backup_before_iot_circuit_lab_$Stamp.zip"

if (!(Test-Path $Root)) {
  Write-Host "Root path not found: $Root" -ForegroundColor Yellow
  Write-Host "Edit this script if your Clawstack path is different."
  exit 1
}

$targets = @()
foreach ($name in @("docker-compose.yml", "portal", "node-red", "n8n", "README.md")) {
  $p = Join-Path $Root $name
  if (Test-Path $p) { $targets += $p }
}

if ($targets.Count -eq 0) {
  Write-Host "No backup targets found." -ForegroundColor Yellow
  exit 1
}

Compress-Archive -Path $targets -DestinationPath $Backup -Force
Write-Host "Backup created: $Backup" -ForegroundColor Cyan
