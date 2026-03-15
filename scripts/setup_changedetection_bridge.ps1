$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\changedetection_bridge"
$configFile = Join-Path $stateDir "config.json"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

$username = "meshbot"
$email = "meshbot@example.com"
$password = "MeshBot-20260313!"
$vikunjaBase = "http://127.0.0.1:3456/api/v1"
$projectTitle = "Changedetection Inbox"
$ntfyBase = "http://127.0.0.1:8091"
$ntfyTopic = "clawstack-watch"

try {
  Invoke-WebRequest -Method Post -Uri "$vikunjaBase/register" -ContentType "application/json" -Body (@{
    username = $username
    email = $email
    password = $password
  } | ConvertTo-Json) -UseBasicParsing -TimeoutSec 120 | Out-Null
} catch {
}

$token = (Invoke-RestMethod -Method Post -Uri "$vikunjaBase/login" -ContentType "application/json" -Body (@{
  username = $username
  password = $password
  long_token = $true
} | ConvertTo-Json) -TimeoutSec 300).token

$headers = @{ Authorization = "Bearer $token" }
$projects = Invoke-RestMethod -Method Get -Uri "$vikunjaBase/projects" -Headers $headers -TimeoutSec 300
$project = $projects | Where-Object { $_.title -eq $projectTitle } | Select-Object -First 1
if (-not $project) {
  $project = Invoke-RestMethod -Method Put -Uri "$vikunjaBase/projects" -Headers $headers -ContentType "application/json" -Body (@{
    title = $projectTitle
    description = "Auto-created tasks from local Changedetection bridge."
  } | ConvertTo-Json) -TimeoutSec 300
}

$config = @{
  vikunja = @{
    baseUrl = $vikunjaBase
    username = $username
    email = $email
    password = $password
    token = $token
    projectId = $project.id
    projectTitle = $project.title
  }
  ntfy = @{
    baseUrl = $ntfyBase
    topic = $ntfyTopic
  }
  updatedAt = (Get-Date).ToString("o")
}

$config | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $configFile
Write-Output ($config | ConvertTo-Json -Depth 6)
