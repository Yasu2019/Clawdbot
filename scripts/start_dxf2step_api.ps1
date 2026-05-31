#Requires -Version 5.1
<#
.SYNOPSIS
  Keep DXF2STEP FastAPI alive on http://127.0.0.1:8002 (SJP-3 gap job + gdt_overlay).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\start_dxf2step_api.ps1
  powershell -ExecutionPolicy Bypass -File scripts\start_dxf2step_api.ps1 -Restart
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [int]$Port = 8002,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$apiScript = Join-Path $RepoRoot "data\workspace\apps\dxf2step\dxf2step_api.py"
$statusPath = Join-Path $RepoRoot "data\workspace\dxf2step_api_status.json"
$healthUrl = "http://127.0.0.1:$Port/api/dxf2step/health"

function Test-Dxf2StepHealth {
    try {
        $r = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 4
        return ($r.status -eq "ok")
    } catch {
        return $false
    }
}

if (-not (Test-Path $apiScript)) {
    throw "Missing API script: $apiScript"
}

if ($Restart) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -match "python") {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Write-Host "[OK] Stopped PID $($proc.Id) on port $Port"
        }
    }
    Start-Sleep -Seconds 2
}

if (Test-Dxf2StepHealth) {
    Write-Host "[OK] DXF2STEP API already online: $healthUrl"
} else {
    Write-Host "[start] Launching dxf2step_api on port $Port..."
    Start-Process -FilePath "python" -ArgumentList @($apiScript) -WorkingDirectory (Split-Path $apiScript) -WindowStyle Minimized
    $deadline = (Get-Date).AddSeconds(30)
    $ok = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-Dxf2StepHealth) {
            $ok = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ok) {
        throw "DXF2STEP API did not respond on $healthUrl within 30s"
    }
    Write-Host "[OK] DXF2STEP API online: $healthUrl"
}

$status = @{
    updated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    port = $Port
    health_url = $healthUrl
    online = $true
} | ConvertTo-Json
Set-Content -Path $statusPath -Value $status -Encoding UTF8
Write-Host "[OK] status -> $statusPath"
