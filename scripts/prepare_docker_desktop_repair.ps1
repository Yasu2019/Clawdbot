$ErrorActionPreference = "Stop"

$repoRoot = "D:\Clawdbot_Docker_20260125"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupRoot = Join-Path $repoRoot "backups\docker_desktop_repair\$timestamp"
$dockerAppData = Join-Path $env:APPDATA "Docker"
$dockerLocalData = Join-Path $env:LOCALAPPDATA "Docker"
$settingsPath = Join-Path $dockerAppData "settings-store.json"
$statusPath = Join-Path $repoRoot "data\workspace\docker_desktop_repair_prepare_status.json"

New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

$status = [ordered]@{
  preparedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
  backupRoot = $backupRoot
  files = @()
  dockerVersion = $null
  dockerInfoOk = $false
  customWslDistroDir = $null
  dDriveFreeGB = [math]::Round((Get-PSDrive D).Free / 1GB, 2)
  eDriveFreeGB = [math]::Round((Get-PSDrive E).Free / 1GB, 2)
}

function Copy-IfExists {
  param(
    [string]$Source,
    [string]$DestinationName
  )

  if (Test-Path $Source) {
    $dest = Join-Path $backupRoot $DestinationName
    Copy-Item -LiteralPath $Source -Destination $dest -Force
    $status.files += $dest
  }
}

Copy-IfExists -Source $settingsPath -DestinationName "settings-store.json"
Copy-IfExists -Source (Join-Path $dockerAppData "features-overrides.json") -DestinationName "features-overrides.json"
Copy-IfExists -Source (Join-Path $dockerAppData "unleash-v2-docker-desktop.json") -DestinationName "unleash-v2-docker-desktop.json"
Copy-IfExists -Source (Join-Path $dockerLocalData "log\host\com.docker.backend.exe.log") -DestinationName "com.docker.backend.exe.log"
Copy-IfExists -Source (Join-Path $dockerLocalData "log\host\Docker Desktop.exe.log") -DestinationName "Docker Desktop.exe.log"

if (Test-Path $settingsPath) {
  $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
  $status.customWslDistroDir = $settings.CustomWslDistroDir
}

try {
  $status.dockerVersion = (& docker version --format '{{.Server.Version}}' 2>$null)
  & docker info 1>$null 2>$null
  $status.dockerInfoOk = $true
} catch {
  $status.dockerVersion = "unavailable"
  $status.dockerInfoOk = $false
}

$status | ConvertTo-Json -Depth 6 | Set-Content -Path $statusPath -Encoding UTF8
Get-Content $statusPath -Raw
