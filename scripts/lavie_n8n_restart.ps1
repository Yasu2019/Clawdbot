#Requires -Version 5.1
<#
.SYNOPSIS
  Restart LAVIE satellite docker stack (n8n + exec_bridge host). Run ON LAVIE or via job worker.
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\clawstack_satellite",
    [int]$N8nPort = 5679
)

$ErrorActionPreference = "Continue"

if (-not (Test-Path $InstallRoot)) {
    Write-Error "InstallRoot not found: $InstallRoot"
    exit 1
}

Write-Host "[n8n-restart] Docker satellite stack at $InstallRoot"
Push-Location $InstallRoot
try {
    & docker compose down 2>&1 | ForEach-Object { Write-Host $_ }
    Start-Sleep -Seconds 2
    & docker compose up -d 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker compose up failed exit=$LASTEXITCODE"
        exit 1
    }
} finally {
    Pop-Location
}

$deadline = (Get-Date).AddSeconds(90)
$ok = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$N8nPort/healthz" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) {
            $ok = $true
            Write-Host "[OK] n8n healthz: $($r.Content)"
            break
        }
    } catch {
        Start-Sleep -Seconds 3
    }
}

if (-not $ok) {
    Write-Error "n8n healthz timeout on port $N8nPort"
    exit 1
}

Write-Host "N8N_RESTART_OK port=$N8nPort"
