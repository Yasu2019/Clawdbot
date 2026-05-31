#Requires -Version 5.1
<#
.SYNOPSIS
  Repair UTF-8 BOM in satellite .env (docker compose parse error on Windows).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\lavie_usb_pack\scripts\lavie_repair_env.ps1
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\clawstack_satellite"
)

$ErrorActionPreference = "Stop"

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

$envPath = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envPath)) {
    throw ".env not found: $envPath"
}

$raw = [System.IO.File]::ReadAllText($envPath)
if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
    $raw = $raw.Substring(1)
    Write-Host "[FIX] Removed UTF-8 BOM from $envPath"
} else {
    Write-Host "[OK] No BOM detected; rewriting as UTF-8 without BOM"
}

Write-Utf8NoBom -Path $envPath -Content $raw
Write-Host "[OK] Repaired $envPath"
Write-Host "Next: start Docker Desktop, then run:"
Write-Host "  cd $InstallRoot"
Write-Host "  docker compose build"
Write-Host "  docker compose up -d"
