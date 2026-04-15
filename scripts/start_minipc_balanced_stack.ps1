param(
  [switch]$DryRun,
  [ValidateSet("balanced", "full")]
  [string]$Mode = "balanced"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$statusDir = Join-Path $repoRoot "data\state\minipc_balanced_stack"
$statusPath = Join-Path $statusDir "startup_status.json"
$logPath = Join-Path $statusDir "startup.log"
$phaseDelaySeconds = 8
$healthTimeoutSeconds = 75

New-Item -ItemType Directory -Force -Path $statusDir | Out-Null

function Write-Log {
  param([string]$Message)
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -Path $logPath -Value $line -Encoding UTF8
}

function Test-HttpReady {
  param(
    [string[]]$Urls,
    [int]$TimeoutSeconds = 60
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    foreach ($url in $Urls) {
      try {
        Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 5 | Out-Null
        return $true
      } catch {
        continue
      }
    }
    Start-Sleep -Seconds 2
  }
  return $false
}

function Test-ContainerRunning {
  param([string]$ServiceToken)
  try {
    $names = docker ps --format "{{.Names}}" 2>$null
    return @($names | Where-Object { $_ -match [regex]::Escape($ServiceToken) }).Count -gt 0
  } catch {
    return $false
  }
}

function Start-DockerService {
  param(
    [string]$ComposeFile,
    [string]$ServiceName,
    [string[]]$ProbeUrls = @()
  )

  if (Test-ContainerRunning -ServiceToken $ServiceName) {
    Write-Log "SKIP already running docker service: $ServiceName"
    return [ordered]@{
      name = $ServiceName
      kind = "docker"
      status = "already_running"
      composeFile = $ComposeFile
    }
  }

  Write-Log "START docker service: $ServiceName via $ComposeFile"
  & docker compose -f $ComposeFile up -d $ServiceName
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to start docker service $ServiceName"
  }

  $ready = $true
  if ($ProbeUrls.Count -gt 0) {
    $ready = Test-HttpReady -Urls $ProbeUrls -TimeoutSeconds $healthTimeoutSeconds
  } else {
    Start-Sleep -Seconds 4
  }

  if (-not $ready) {
    throw "Health probe failed for $ServiceName"
  }

  Write-Log "READY docker service: $ServiceName"
  return [ordered]@{
    name = $ServiceName
    kind = "docker"
    status = "started"
    composeFile = $ComposeFile
    probes = $ProbeUrls
  }
}

function Start-HostScript {
  param(
    [string]$ScriptPath,
    [string]$Name,
    [string[]]$ProbeUrls = @()
  )

  Write-Log "START host script: $Name"
  & $ScriptPath
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to start host script $Name"
  }

  $ready = $true
  if ($ProbeUrls.Count -gt 0) {
    $ready = Test-HttpReady -Urls $ProbeUrls -TimeoutSeconds $healthTimeoutSeconds
  } else {
    Start-Sleep -Seconds 4
  }

  if (-not $ready) {
    throw "Health probe failed for host script $Name"
  }

  Write-Log "READY host script: $Name"
  return [ordered]@{
    name = $Name
    kind = "host-script"
    status = "started"
    scriptPath = $ScriptPath
    probes = $ProbeUrls
  }
}

$dockerBase = Join-Path $repoRoot "docker-compose.yml"
$learningCompose = Join-Path $repoRoot "clawstack_v2\docker-compose.yml"
$learningPatch = Join-Path $repoRoot "clawstack_v2\docker-compose.learning_engine.patch.yml"

$steps = New-Object System.Collections.Generic.List[object]

function Add-Step {
  param([string]$Name, [scriptblock]$Action)
  $steps.Add([ordered]@{
    name = $Name
    result = $null
    startedAt = $null
    endedAt = $null
    ok = $false
    error = $null
    action = $Action
  }) | Out-Null
}

Add-Step -Name "postgres" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "postgres" }
Add-Step -Name "redis" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "redis" }
Add-Step -Name "qdrant" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "qdrant" }
Add-Step -Name "ollama" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "ollama" -ProbeUrls @("http://127.0.0.1:11434/api/tags") }
Add-Step -Name "clawdbot-gateway" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "clawdbot-gateway" }
Add-Step -Name "portal_server" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "portal_server" }
Add-Step -Name "litellm" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "litellm" }
Add-Step -Name "n8n" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "n8n" }
Add-Step -Name "learning_engine" -Action {
  if (Test-ContainerRunning -ServiceToken "learning_engine") {
    Write-Log "SKIP already running docker service: learning_engine"
    return [ordered]@{ name = "learning_engine"; kind = "docker"; status = "already_running" }
  }
  Write-Log "START docker service: learning_engine via learning_engine patch"
  & docker compose -f $learningCompose -f $learningPatch up -d qdrant learning_engine
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to start learning_engine"
  }
  if (-not (Test-HttpReady -Urls @("http://127.0.0.1:8110/health", "http://localhost:8110/health") -TimeoutSeconds $healthTimeoutSeconds)) {
    throw "learning_engine health probe failed"
  }
  Write-Log "READY docker service: learning_engine"
  return [ordered]@{ name = "learning_engine"; kind = "docker"; status = "started"; probes = @("http://127.0.0.1:8110/health") }
}
Add-Step -Name "email_search_api" -Action { Start-HostScript -ScriptPath (Join-Path $repoRoot "scripts\start_email_search_api.ps1") -Name "email_search_api" -ProbeUrls @("http://127.0.0.1:8792/api/stats") }
Add-Step -Name "email_blacklist_hub" -Action { Start-HostScript -ScriptPath (Join-Path $repoRoot "scripts\start_email_blacklist_hub_api.ps1") -Name "email_blacklist_hub" -ProbeUrls @("http://127.0.0.1:8791/api/email-blacklist/candidates") }
Add-Step -Name "email_continuous_watchdog" -Action { Start-HostScript -ScriptPath (Join-Path $repoRoot "scripts\start_email_continuous_watchdog.ps1") -Name "email_continuous_watchdog" }
Add-Step -Name "telegram_fast_bridge" -Action { Start-HostScript -ScriptPath (Join-Path $repoRoot "scripts\start_telegram_fast_bridge.ps1") -Name "telegram_fast_bridge" }

if ($Mode -eq "full") {
  Add-Step -Name "minio" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "minio" }
  Add-Step -Name "searxng" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "searxng" }
  Add-Step -Name "open_webui" -Action { Start-DockerService -ComposeFile $dockerBase -ServiceName "open_webui" }
}

$results = New-Object System.Collections.Generic.List[object]
$startedAt = Get-Date
Write-Log "Balanced startup begin"

if ($DryRun) {
  $dryStatus = [ordered]@{
    updatedAt = (Get-Date).ToString("s")
    mode = "balanced"
    dryRun = $true
    phaseDelaySeconds = $phaseDelaySeconds
    healthTimeoutSeconds = $healthTimeoutSeconds
    plannedSteps = @($steps | ForEach-Object { $_.name })
  }
  $dryStatus | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
  Write-Log "Balanced startup dry run finished"
  Write-Output "minipc balanced startup dry-run finished"
  exit 0
}

foreach ($step in $steps) {
  $step.startedAt = (Get-Date).ToString("s")
  try {
    $step.result = & $step.action
    $step.ok = $true
    $step.endedAt = (Get-Date).ToString("s")
  } catch {
    $step.ok = $false
    $step.error = $_.Exception.Message
    $step.endedAt = (Get-Date).ToString("s")
    Write-Log "ERROR $($step.name): $($step.error)"
    $results.Add([ordered]@{
      name = $step.name
      ok = $false
      error = $step.error
      startedAt = $step.startedAt
      endedAt = $step.endedAt
    }) | Out-Null
    break
  }

  $results.Add([ordered]@{
    name = $step.name
    ok = $true
    result = $step.result
    startedAt = $step.startedAt
    endedAt = $step.endedAt
  }) | Out-Null

  Start-Sleep -Seconds $phaseDelaySeconds
}

$overallOk = ($results.Count -eq $steps.Count)
$status = [ordered]@{
  updatedAt = (Get-Date).ToString("s")
  mode = $Mode
  ok = $overallOk
  phaseDelaySeconds = $phaseDelaySeconds
  healthTimeoutSeconds = $healthTimeoutSeconds
  startedAt = $startedAt.ToString("s")
  endedAt = (Get-Date).ToString("s")
  steps = $results
}

$status | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Log ("Balanced startup end ok={0}" -f $overallOk)
Write-Output ("minipc balanced startup finished ok={0}" -f $overallOk)
