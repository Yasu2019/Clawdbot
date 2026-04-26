Param(
  [string]$TargetRoot = "D:\Clawdbot_Docker_20260125\ace_step_stack"
)

$ErrorActionPreference = "Stop"
Write-Host "[ACE-Step] Windows bootstrap start: $TargetRoot"

$dirs = @(
  $TargetRoot,
  "$TargetRoot\runtime",
  "$TargetRoot\models",
  "$TargetRoot\outputs",
  "$TargetRoot\logs",
  "$TargetRoot\portal_stub",
  "$TargetRoot\configs",
  "$TargetRoot\scripts"
)

foreach ($d in $dirs) {
  New-Item -ItemType Directory -Path $d -Force | Out-Null
}

Write-Host "[ACE-Step] Checking winget packages"
$packages = @(
  @{ id = "Git.Git"; name = "Git" },
  @{ id = "Docker.DockerDesktop"; name = "Docker Desktop" },
  @{ id = "Python.Python.3.11"; name = "Python 3.11" }
)

foreach ($pkg in $packages) {
  try {
    winget list --id $pkg.id | Out-Null
  } catch {
    Write-Host "[ACE-Step] Installing $($pkg.name)"
    winget install --id $pkg.id -e --accept-package-agreements --accept-source-agreements
  }
}

Write-Host "[ACE-Step] Enabling WSL if needed"
wsl --install -d Ubuntu | Out-Null

Write-Host "[ACE-Step] Copy sample env if missing"
$zipRoot = Split-Path -Parent $PSScriptRoot
$envSrc = Join-Path $zipRoot "configs\.env.example"
$envDst = Join-Path $TargetRoot ".env"
if (-not (Test-Path $envDst)) {
  Copy-Item $envSrc $envDst -Force
}

Copy-Item (Join-Path $zipRoot "configs\docker-compose.ace-stack.yml") "$TargetRoot\docker-compose.yml" -Force
Copy-Item (Join-Path $zipRoot "portal_stub\index.html") "$TargetRoot\portal_stub\index.html" -Force

Write-Host "[ACE-Step] Windows bootstrap complete"
