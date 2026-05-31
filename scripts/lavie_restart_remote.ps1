#Requires -Version 5.1
<#
.SYNOPSIS
  Queue LAVIE boost+restart in a detached process (safe when triggered via job worker HTTP).
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [int]$DelaySec = 5
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$restartScript = Join-Path $RepoRoot "scripts\lavie_restart_all.ps1"
$log = Join-Path $env:TEMP "lavie_restart_all.log"

$arg = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
    "Start-Sleep -Seconds $DelaySec; & '$restartScript' -RepoRoot '$RepoRoot' *>&1 | Out-File -FilePath '$log' -Encoding utf8"
)

Start-Process -FilePath "powershell.exe" -ArgumentList $arg -WindowStyle Normal
Write-Host "RESTART_QUEUED_OK delay=${DelaySec}s log=$log"
