# Read-only Clawstack/OpenClaw environment audit for Windows PowerShell.
# This script must not modify files, Docker, DB, or environment.
# Run only after Claude/Codex review.

$ErrorActionPreference = "Continue"

Write-Host "=== OpenClaw / Clawstack Read-only Audit ==="
Write-Host "Timestamp: $(Get-Date -Format o)"
Write-Host ""

Write-Host "## Host"
Write-Host "ComputerName: $env:COMPUTERNAME"
Write-Host "UserName: $env:USERNAME"
Write-Host "OS:"
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture | Format-List

Write-Host "## Candidate roots"
$candidates = @(
  "D:\Clawdbot_Docker_20260125",
  "D:\Clawdbot_Docker_20260125\clawstack_v2",
  "C:\Users\$env:USERNAME",
  "$PWD"
)
foreach ($p in $candidates) {
  if (Test-Path $p) {
    Write-Host "[FOUND] $p"
  } else {
    Write-Host "[MISS ] $p"
  }
}

Write-Host ""
Write-Host "## Docker version"
docker --version 2>$null

Write-Host ""
Write-Host "## Running containers"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>$null

Write-Host ""
Write-Host "## Docker volumes"
docker volume ls 2>$null

Write-Host ""
Write-Host "## Docker networks"
docker network ls 2>$null

Write-Host ""
Write-Host "## Listening TCP ports"
Get-NetTCPConnection -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess | Sort-Object LocalPort | Format-Table -AutoSize

Write-Host ""
Write-Host "## Compose files under candidate roots"
foreach ($root in $candidates) {
  if (Test-Path $root) {
    Get-ChildItem -Path $root -Filter "docker-compose*.yml" -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
    Get-ChildItem -Path $root -Filter "compose*.yml" -Recurse -ErrorAction SilentlyContinue | Select-Object FullName
  }
}

Write-Host ""
Write-Host "## .env files existence only; contents are NOT printed"
foreach ($root in $candidates) {
  if (Test-Path $root) {
    Get-ChildItem -Path $root -Filter ".env*" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
      Write-Host "[ENV EXISTS] $($_.FullName)"
    }
  }
}

Write-Host ""
Write-Host "Audit complete. No changes were made."
