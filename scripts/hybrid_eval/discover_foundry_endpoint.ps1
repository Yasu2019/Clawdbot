param(
  [string]$OutPath = "tmp/foundrylocal_phase0/foundry_discovery.json",
  [string]$HostName = "127.0.0.1",
  [int[]]$Ports = @(8000, 8080, 5000, 11435, 11436, 9000),
  [int]$TimeoutSec = 2
)

$ErrorActionPreference = "Stop"

function Try-GetJson([string]$Url) {
  try {
    return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec
  } catch {
    return $null
  }
}

$results = @()
foreach ($p in $Ports) {
  $base = "http://$HostName`:$p"
  $models = Try-GetJson "$base/v1/models"
  $health = Try-GetJson "$base/health"

  $hit = $false
  if ($models) { $hit = $true }
  if ($health) { $hit = $true }

  $results += [pscustomobject]@{
    port = $p
    base_url_v1 = "$base/v1"
    models_ok = [bool]$models
    health_ok = [bool]$health
  }
}

$payload = [ordered]@{
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  host = $HostName
  ports = $Ports
  results = $results
}

$dir = Split-Path -Parent $OutPath
if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$payload | ConvertTo-Json -Depth 6 | Out-File -LiteralPath $OutPath -Encoding UTF8

Write-Host $OutPath

