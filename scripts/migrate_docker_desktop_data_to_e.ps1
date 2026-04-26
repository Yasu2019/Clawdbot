$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$settingsPath = "C:\Users\yasu\AppData\Roaming\Docker\settings-store.json"
$settingsBackup = "$settingsPath.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$srcRoot = "D:\DockerData\DockerDesktopWSL"
$dstRoot = "E:\DockerData\DockerDesktopWSL"
$statusPath = "D:\Clawdbot_Docker_20260125\data\workspace\docker_data_root_migration_status.json"

function Save-Status($payload) {
  $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

function Stop-DockerDesktop {
  Get-Process "Docker Desktop","com.docker.backend" -ErrorAction SilentlyContinue | ForEach-Object {
    try { Stop-Process -Id $_.Id -Force -ErrorAction Stop } catch {}
  }
  Start-Sleep -Seconds 5
  wsl --shutdown | Out-Null
  Start-Sleep -Seconds 3
}

function Start-DockerDesktop {
  Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
}

$status = [ordered]@{
  startedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
  source = $srcRoot
  destination = $dstRoot
  ok = $false
}
Save-Status $status

if (!(Test-Path -LiteralPath $srcRoot)) {
  throw "Source Docker Desktop WSL root not found: $srcRoot"
}

if (!(Test-Path -LiteralPath (Split-Path -Parent $dstRoot))) {
  New-Item -ItemType Directory -Path (Split-Path -Parent $dstRoot) -Force | Out-Null
}

Copy-Item -LiteralPath $settingsPath -Destination $settingsBackup -Force
$status.settingsBackup = $settingsBackup
Save-Status $status

Stop-DockerDesktop
$status.stoppedDocker = $true
Save-Status $status

robocopy $srcRoot $dstRoot /E /MOVE /COPY:DAT /DCOPY:DAT /R:2 /W:2 /NFL /NDL /NP /MT:16 | Out-Null
$status.robocopyExitCode = $LASTEXITCODE
if ($LASTEXITCODE -gt 7) {
  throw "Robocopy failed with exit code $LASTEXITCODE"
}
Save-Status $status

if (Test-Path -LiteralPath $srcRoot) {
  $remaining = (Get-ChildItem -LiteralPath $srcRoot -Force -ErrorAction SilentlyContinue | Measure-Object).Count
  if ($remaining -gt 0) {
    throw "Source still contains $remaining item(s): $srcRoot"
  }
  Remove-Item -LiteralPath $srcRoot -Force -Recurse -ErrorAction SilentlyContinue
}

$settings = Get-Content -Raw -LiteralPath $settingsPath | ConvertFrom-Json
$settings.CustomWslDistroDir = $dstRoot
$settings | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
$status.updatedSettings = $true
Save-Status $status

if (!(Test-Path -LiteralPath $srcRoot)) {
  New-Item -ItemType Junction -Path $srcRoot -Target $dstRoot | Out-Null
  $status.junctionCreated = $true
}
Save-Status $status

Start-DockerDesktop
$status.startedDocker = $true
$status.ok = $true
$status.finishedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
Save-Status $status

Write-Output "Docker Desktop data migration completed."
