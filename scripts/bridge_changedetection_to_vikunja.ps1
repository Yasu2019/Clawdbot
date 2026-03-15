$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$watchRoot = Join-Path $repoRoot "clawstack_v2\data\changedetection"
$stateDir = Join-Path $repoRoot "data\state\changedetection_bridge"
$configFile = Join-Path $stateDir "config.json"
$stateFile = Join-Path $stateDir "state.json"
$statusFile = Join-Path $stateDir "harness_status.json"
$n8nFlowConfigFile = Join-Path $repoRoot "data\state\n8n_changedetection_flow\config.json"

function Write-Status {
  param([string]$State, [hashtable]$Extra = @{})
  $payload = @{
    service = "changedetection_to_vikunja_bridge"
    updatedAt = (Get-Date).ToString("o")
    state = $State
  }
  foreach ($key in $Extra.Keys) {
    $payload[$key] = $Extra[$key]
  }
  $payload | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $statusFile
}

function Send-Ntfy {
  param($Config, [string]$Title, [string]$Body)
  Invoke-RestMethod -Method Post -Uri "$($Config.ntfy.baseUrl)/$($Config.ntfy.topic)" -Body $Body -Headers @{
    Title = $Title
    Priority = "default"
    Tags = "eyes,mag"
  } | Out-Null
}

function New-VikunjaTask {
  param($Config, [string]$Title, [string]$Description)
  $headers = @{ Authorization = "Bearer $($Config.vikunja.token)" }
  return Invoke-RestMethod -Method Put -Uri "$($Config.vikunja.baseUrl)/projects/$($Config.vikunja.projectId)/tasks" -Headers $headers -ContentType "application/json" -Body (@{
    title = $Title
    description = $Description
  } | ConvertTo-Json) -TimeoutSec 300
}

function Get-N8nFlowConfig {
  if (Test-Path $n8nFlowConfigFile) {
    try {
      return Get-Content -Raw $n8nFlowConfigFile | ConvertFrom-Json
    } catch {
      return $null
    }
  }
  return $null
}

function Send-N8nEvent {
  param(
    $N8nConfig,
    [hashtable]$Payload
  )
  if (-not $N8nConfig -or -not $N8nConfig.n8n -or -not $N8nConfig.n8n.webhookUrl) {
    return $null
  }
  return Invoke-RestMethod -Method Post -Uri $N8nConfig.n8n.webhookUrl -ContentType "application/json" -Body ($Payload | ConvertTo-Json -Depth 10) -TimeoutSec 60
}

function Ensure-Config {
  if (-not (Test-Path $configFile)) {
    powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\setup_changedetection_bridge.ps1") | Out-Null
  }
  return Get-Content -Raw $configFile | ConvertFrom-Json
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
$config = Ensure-Config
$n8nFlowConfig = Get-N8nFlowConfig
$state = @{ watches = @{} }
if (Test-Path $stateFile) {
  try {
    $rawState = Get-Content -Raw $stateFile | ConvertFrom-Json
    if ($rawState.watches) {
      foreach ($prop in $rawState.watches.PSObject.Properties) {
        $state.watches[$prop.Name] = @{
          title = $prop.Value.title
          url = $prop.Value.url
          lastChecksum = $prop.Value.lastChecksum
          lastChecked = $prop.Value.lastChecked
          initializedAt = $prop.Value.initializedAt
          lastNotifiedAt = $prop.Value.lastNotifiedAt
          lastTaskId = $prop.Value.lastTaskId
        }
      }
    }
  } catch {
  }
}

$once = $args -contains "--once"
Write-Status -State "starting" -Extra @{ once = $once }

do {
  $watchDirs = Get-ChildItem $watchRoot -Directory | Where-Object { Test-Path (Join-Path $_.FullName "watch.json") }
  $changes = @()

  foreach ($dir in $watchDirs) {
    $watch = Get-Content -Raw (Join-Path $dir.FullName "watch.json") | ConvertFrom-Json
    $checksumPath = Join-Path $dir.FullName "last-checksum.txt"
    if (-not (Test-Path $checksumPath)) { continue }
    $checksum = (Get-Content -Raw $checksumPath).Trim()
    $key = $watch.uuid
    $existing = $state.watches[$key]

    if (-not $existing) {
      $state.watches[$key] = @{
        title = $(if ($watch.title) { $watch.title } elseif ($watch.page_title) { $watch.page_title } else { $watch.url })
        url = $watch.url
        lastChecksum = $checksum
        lastChecked = $watch.last_checked
        initializedAt = (Get-Date).ToString("o")
      }
      continue
    }

    if ($existing.lastChecksum -ne $checksum -and $watch.last_checked -ne $existing.lastChecked) {
      $title = if ($watch.title) { $watch.title } elseif ($watch.page_title) { $watch.page_title } else { $watch.url }
      $message = "Changedetection detected an update.`nTitle: $title`nURL: $($watch.url)`nChecked: $($watch.last_checked)"
      try {
        Send-Ntfy -Config $config -Title "Changedetection update: $title" -Body $message
      } catch {
      }
      $task = $null
      try {
        $task = New-VikunjaTask -Config $config -Title "Check update: $title" -Description $message
      } catch {
      }
      $n8nResponse = $null
      try {
        $n8nPayload = @{
          source = "changedetection_bridge"
          title = $title
          url = $watch.url
          summary = $message
          checkedAt = $watch.last_checked
          taskId = $(if ($task) { $task.id } else { $null })
          ntfyTopic = $config.ntfy.topic
        }
        $n8nResponse = Send-N8nEvent -N8nConfig $n8nFlowConfig -Payload $n8nPayload
      } catch {
      }
      $existing.lastChecksum = $checksum
      $existing.lastChecked = $watch.last_checked
      $existing.lastNotifiedAt = (Get-Date).ToString("o")
      if ($task) {
        $existing.lastTaskId = $task.id
      }
      if ($n8nResponse) {
        $existing.lastWorkflowReceiptAt = $n8nResponse.receivedAt
      }
      $changes += @{
        title = $title
        url = $watch.url
        taskId = $(if ($task) { $task.id } else { $null })
        n8nReceivedAt = $(if ($n8nResponse) { $n8nResponse.receivedAt } else { $null })
      }
    }
  }

  $state.updatedAt = (Get-Date).ToString("o")
  $state | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $stateFile

  Write-Status -State "idle" -Extra @{
    watchCount = $watchDirs.Count
    changeCount = $changes.Count
    changes = $changes
    projectId = $config.vikunja.projectId
    ntfyTopic = $config.ntfy.topic
    n8nWebhook = $(if ($n8nFlowConfig) { $n8nFlowConfig.n8n.webhookUrl } else { $null })
  }

  if (-not $once) {
    Start-Sleep -Seconds 180
  }
} while (-not $once)
