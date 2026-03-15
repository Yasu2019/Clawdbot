$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot "config\app_mesh.json"
$stateDir = Join-Path $repoRoot "data\state\app_mesh"
$statusFile = Join-Path $stateDir "harness_status.json"
$stateFile = Join-Path $stateDir "state.json"

function Write-Status {
  param(
    [string]$State,
    [hashtable]$Extra = @{}
  )
  $payload = @{
    service = "app_mesh_watch"
    updatedAt = (Get-Date).ToString("o")
    state = $State
  }
  foreach ($key in $Extra.Keys) {
    $payload[$key] = $Extra[$key]
  }
  $payload | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $statusFile
}

function Send-Ntfy {
  param(
    [string]$BaseUrl,
    [string]$Topic,
    [string]$Title,
    [string]$Message,
    [string]$Priority = "default",
    [string]$Tags = "warning"
  )
  try {
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/$Topic" -Body $Message -Headers @{
      Title = $Title
      Priority = $Priority
      Tags = $Tags
    } | Out-Null
  } catch {
  }
}

function Test-ServiceEndpoint {
  param($Service)
  try {
    $response = Invoke-WebRequest -Uri $Service.url -Method $Service.method -TimeoutSec 20 -UseBasicParsing
    return @{
      ok = ($response.StatusCode -eq [int]$Service.expectedStatus)
      statusCode = [int]$response.StatusCode
      error = $null
    }
  } catch {
    $statusCode = 0
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      $statusCode = [int]$_.Exception.Response.StatusCode
    }
    return @{
      ok = ($statusCode -eq [int]$Service.expectedStatus)
      statusCode = $statusCode
      error = $_.Exception.Message
    }
  }
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$config = Get-Content -Raw $configPath | ConvertFrom-Json
$state = @{ services = @{} }
if (Test-Path $stateFile) {
  try {
    $rawState = Get-Content -Raw $stateFile | ConvertFrom-Json
    if ($rawState.services) {
      foreach ($prop in $rawState.services.PSObject.Properties) {
        $state.services[$prop.Name] = @{
          state = $prop.Value.state
          url = $prop.Value.url
          statusCode = $prop.Value.statusCode
          error = $prop.Value.error
          checkedAt = $prop.Value.checkedAt
          group = $prop.Value.group
        }
      }
    }
  } catch {
  }
}

$once = $args -contains "--once"
Write-Status -State "starting" -Extra @{ once = $once; totalServices = $config.services.Count }

do {
  $results = @()
  foreach ($service in $config.services) {
    $probe = Test-ServiceEndpoint -Service $service
    $name = $service.name
    $nowState = if ($probe.ok) { "up" } else { "down" }
    $prevState = if ($state.services.ContainsKey($name)) { $state.services[$name].state } else { "unknown" }

    if ($prevState -ne "unknown" -and $prevState -ne $nowState) {
      $title = "Clawstack service ${nowState}: $name"
      $message = "$name changed from $prevState to $nowState.`nURL: $($service.url)`nStatus: $($probe.statusCode)`nTime: $(Get-Date -Format o)"
      $priority = if ($nowState -eq "down") { "high" } else { "default" }
      $tags = if ($nowState -eq "down") { "rotating_light,warning" } else { "white_check_mark" }
      Send-Ntfy -BaseUrl $config.ntfy.baseUrl -Topic $config.ntfy.topic -Title $title -Message $message -Priority $priority -Tags $tags
    }

    $entry = @{
      state = $nowState
      url = $service.url
      statusCode = $probe.statusCode
      error = $probe.error
      checkedAt = (Get-Date).ToString("o")
      group = $service.group
    }
    $state.services[$name] = $entry
    $results += @{
      name = $name
      group = $service.group
      state = $nowState
      statusCode = $probe.statusCode
      error = $probe.error
    }
  }

  $state.updatedAt = (Get-Date).ToString("o")
  $state | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $stateFile

  $downCount = @($results | Where-Object { $_.state -eq "down" }).Count
  Write-Status -State ($(if ($downCount -gt 0) { "degraded" } else { "healthy" })) -Extra @{
    downCount = $downCount
    services = $results
  }

  if (-not $once) {
    Start-Sleep -Seconds 120
  }
} while (-not $once)
