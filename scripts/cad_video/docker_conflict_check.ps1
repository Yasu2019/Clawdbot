# Read-only Docker conflict check
$ErrorActionPreference = "Continue"
$portsToCheck = @(6333,9000,9001,6379,11434,5432,8081,8083,8188,7860)
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $PSScriptRoot "..\reports\docker_conflict_$ts.txt"

"Docker/Port Conflict Check - $ts" | Out-File $out -Encoding utf8
"This script is read-only." | Out-File $out -Append -Encoding utf8

foreach ($p in $portsToCheck) {
  $conn = Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue
  if ($conn) {
    "PORT $p : IN USE" | Out-File $out -Append -Encoding utf8
  } else {
    "PORT $p : free" | Out-File $out -Append -Encoding utf8
  }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
  "`n=== docker ps ===" | Out-File $out -Append -Encoding utf8
  docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}" | Out-File $out -Append -Encoding utf8
} else {
  "Docker not found." | Out-File $out -Append -Encoding utf8
}

Write-Host "Docker conflict check complete: $out"
