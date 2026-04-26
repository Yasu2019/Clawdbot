param(
  [string]$Target = "D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios"
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $PSScriptRoot
Write-Host "Source: $Source"
Write-Host "Target: $Target"

if (!(Test-Path $Target)) {
  New-Item -ItemType Directory -Force -Path $Target | Out-Null
}

Copy-Item -Path "$Source\*" -Destination $Target -Recurse -Force
Write-Host "Installed. Next:"
Write-Host "cd $Target"
Write-Host "python scripts\run_review.py --mode full --root .."
