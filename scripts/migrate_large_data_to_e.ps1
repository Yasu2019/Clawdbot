$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = Split-Path -Parent $PSScriptRoot
$destBase = "E:\ClawstackData"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $repoRoot "data\workspace\storage_migration_status_$timestamp.json"

$mappings = @(
  @{ Source = (Join-Path $repoRoot "backups"); Destination = (Join-Path $destBase "backups") },
  @{ Source = (Join-Path $repoRoot "data\workspace"); Destination = (Join-Path $destBase "workspace") },
  @{ Source = (Join-Path $repoRoot "clawstack_v2\data"); Destination = (Join-Path $destBase "clawstack_v2_data") }
)

$stopPatterns = @(
  "email_continuous_watchdog.py",
  "continuous_email_ingest_daemon.py",
  "paperless_rag_watchdog.py",
  "obsidian_vault_watchdog.py",
  "continuous_system_improvement.py",
  "telegram_fast_bridge.js",
  "email_blacklist_hub_api.py"
)

$restartCommands = @(
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_email_continuous_watchdog.ps1") },
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_paperless_rag_watchdog.ps1") },
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_obsidian_vault_watchdog.ps1") },
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_continuous_system_improvement.ps1") },
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1") },
  @{ Type = "powershell"; Path = (Join-Path $repoRoot "scripts\start_email_blacklist_hub_api.ps1") }
)

function Save-Status($payload) {
  $payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $logPath -Encoding UTF8
}

function Get-DirSizeGB([string]$path) {
  if (!(Test-Path -LiteralPath $path)) { return 0 }
  $sum = (Get-ChildItem -LiteralPath $path -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
  return [math]::Round(($sum / 1GB), 2)
}

function Stop-RepoProcesses($patterns) {
  $stopped = @()
  $procs = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -like "python*" -or $_.Name -like "node*" -or $_.Name -like "powershell*") -and
    $_.CommandLine -like "*$repoRoot*"
  }
  foreach ($proc in $procs) {
    foreach ($pattern in $patterns) {
      if ($proc.CommandLine -like "*$pattern*") {
        try {
          Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
          $stopped += [pscustomobject]@{ ProcessId = $proc.ProcessId; Name = $proc.Name; Pattern = $pattern }
        } catch {
          $stopped += [pscustomobject]@{ ProcessId = $proc.ProcessId; Name = $proc.Name; Pattern = $pattern; Error = $_.Exception.Message }
        }
        break
      }
    }
  }
  return $stopped
}

function Invoke-RobocopyMove([string]$source, [string]$destination) {
  if (!(Test-Path -LiteralPath $destination)) {
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
  }
  $arguments = @(
    $source,
    $destination,
    "/E",
    "/MOVE",
    "/COPY:DAT",
    "/DCOPY:DAT",
    "/R:2",
    "/W:2",
    "/NFL",
    "/NDL",
    "/NP",
    "/MT:16"
  )
  $proc = Start-Process -FilePath "robocopy.exe" -ArgumentList $arguments -Wait -PassThru -NoNewWindow
  return $proc.ExitCode
}

function Ensure-Junction([string]$source, [string]$destination) {
  if (Test-Path -LiteralPath $source) {
    $remaining = Get-ChildItem -LiteralPath $source -Force -ErrorAction SilentlyContinue
    if ($remaining.Count -gt 0) {
      throw "Source still contains items after move: $source"
    }
    Remove-Item -LiteralPath $source -Force
  }
  cmd /c "mklink /J `"$source`" `"$destination`"" | Out-Null
}

$status = [ordered]@{
  startedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
  repoRoot = $repoRoot
  destinationBase = $destBase
  mappings = @()
  stoppedProcesses = @()
  dockerDown = $null
  dockerUp = $null
  restarted = @()
  driveBefore = @{}
  driveAfter = @{}
  ok = $false
}

$status.driveBefore = @{
  D = (Get-PSDrive D | Select-Object Name,Free,Used)
  E = (Get-PSDrive E | Select-Object Name,Free,Used)
}
Save-Status $status

if (!(Test-Path -LiteralPath $destBase)) {
  New-Item -ItemType Directory -Path $destBase -Force | Out-Null
}

$status.stoppedProcesses = Stop-RepoProcesses $stopPatterns
Save-Status $status

$down = cmd /c "docker compose down --remove-orphans" 2>&1
$status.dockerDown = $down
Save-Status $status

foreach ($map in $mappings) {
  $entry = [ordered]@{
    source = $map.Source
    destination = $map.Destination
    sourceSizeGB = Get-DirSizeGB $map.Source
    destinationSizeGBBefore = Get-DirSizeGB $map.Destination
    robocopyExitCode = $null
    junctionCreated = $false
  }
  if (!(Test-Path -LiteralPath $map.Source)) {
    $entry.skipped = "missing_source"
    $status.mappings += $entry
    continue
  }
  $exitCode = Invoke-RobocopyMove $map.Source $map.Destination
  $entry.robocopyExitCode = $exitCode
  if ($exitCode -gt 7) {
    throw "Robocopy failed for $($map.Source) -> $($map.Destination) with exit code $exitCode"
  }
  Ensure-Junction $map.Source $map.Destination
  $entry.junctionCreated = $true
  $entry.destinationSizeGBAfter = Get-DirSizeGB $map.Destination
  $status.mappings += $entry
  Save-Status $status
}

$up = cmd /c "docker compose up -d" 2>&1
$status.dockerUp = $up
Save-Status $status

foreach ($cmdInfo in $restartCommands) {
  if (!(Test-Path -LiteralPath $cmdInfo.Path)) { continue }
  try {
    if ($cmdInfo.Type -eq "powershell") {
      $out = powershell -ExecutionPolicy Bypass -File $cmdInfo.Path 2>&1
    } else {
      $out = & $cmdInfo.Path 2>&1
    }
    $status.restarted += [pscustomobject]@{ Path = $cmdInfo.Path; Output = ($out -join "`n") }
  } catch {
    $status.restarted += [pscustomobject]@{ Path = $cmdInfo.Path; Error = $_.Exception.Message }
  }
  Save-Status $status
}

$status.driveAfter = @{
  D = (Get-PSDrive D | Select-Object Name,Free,Used)
  E = (Get-PSDrive E | Select-Object Name,Free,Used)
}
$status.ok = $true
$status.finishedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
Save-Status $status

Write-Output "Migration completed. Status: $logPath"
