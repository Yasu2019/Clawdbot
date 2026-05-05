# Read-only inventory check for OpenClaw / Clawstack V2
# This script does not modify files, Docker containers, volumes, or databases.

$ErrorActionPreference = "Continue"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $PSScriptRoot "..\reports\inventory_$ts"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

"OpenClaw CAD/Video Inventory Check - $ts" | Out-File (Join-Path $outDir "summary.txt") -Encoding utf8

"=== Computer ===" | Out-File (Join-Path $outDir "system.txt") -Encoding utf8
Get-ComputerInfo | Out-File (Join-Path $outDir "system.txt") -Append -Encoding utf8

"=== Disk ===" | Out-File (Join-Path $outDir "disk.txt") -Encoding utf8
Get-PSDrive -PSProvider FileSystem | Format-Table -AutoSize | Out-String | Out-File (Join-Path $outDir "disk.txt") -Append -Encoding utf8

"=== GPU ===" | Out-File (Join-Path $outDir "gpu.txt") -Encoding utf8
Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-Table -AutoSize | Out-String | Out-File (Join-Path $outDir "gpu.txt") -Append -Encoding utf8

"=== Ports ===" | Out-File (Join-Path $outDir "ports.txt") -Encoding utf8
Get-NetTCPConnection -State Listen | Sort-Object LocalPort | Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize | Out-String | Out-File (Join-Path $outDir "ports.txt") -Append -Encoding utf8

"=== Docker ===" | Out-File (Join-Path $outDir "docker.txt") -Encoding utf8
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}" | Out-File (Join-Path $outDir "docker.txt") -Append -Encoding utf8
  "`n=== Docker volumes ===" | Out-File (Join-Path $outDir "docker.txt") -Append -Encoding utf8
  docker volume ls | Out-File (Join-Path $outDir "docker.txt") -Append -Encoding utf8
} else {
  "Docker command not found." | Out-File (Join-Path $outDir "docker.txt") -Append -Encoding utf8
}

Write-Host "Read-only inventory complete: $outDir"
