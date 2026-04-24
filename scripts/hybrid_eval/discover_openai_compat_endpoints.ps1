param(
  [string]$HostName = "127.0.0.1",
  [int]$TimeoutSec = 2,
  [int]$MaxPorts = 80,
  [string]$OutPath = "tmp/foundrylocal_phase0/openai_compat_discovery.json"
)

$ErrorActionPreference = "Stop"

function Try-GetJson([string]$Url) {
  try {
    return Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec $TimeoutSec
  } catch {
    return $null
  }
}

function Try-GetText([string]$Url) {
  try {
    return (Invoke-WebRequest -Method Get -Uri $Url -TimeoutSec $TimeoutSec).Content
  } catch {
    return $null
  }
}

$listenRows = @()
try {
  $listenRows = Get-NetTCPConnection -State Listen -ErrorAction Stop | Select-Object LocalAddress, LocalPort
} catch {
  $listenRows = @()
}

$ports = ($listenRows | Select-Object -ExpandProperty LocalPort -Unique | Sort-Object | Select-Object -First $MaxPorts)
$results = @()

foreach ($p in $ports) {
  $base = "http://$HostName`:$p"
  $v1 = "$base/v1"

  $localAddrs = @()
  $localAddrs = $listenRows | Where-Object { $_.LocalPort -eq $p } | Select-Object -ExpandProperty LocalAddress -Unique
  $localAddrs = $localAddrs | Where-Object { $_ -and $_ -ne "0.0.0.0" -and $_ -ne "::" } | Select-Object -First 5

  $models = Try-GetJson "$v1/models"
  $health = Try-GetJson "$base/health"
  $openapi = Try-GetText "$base/openapi.json"

  $altHit = $null
  if (-not $models -and $localAddrs.Count -gt 0) {
    foreach ($a in $localAddrs) {
      $b2 = "http://$a`:$p"
      $m2 = Try-GetJson "$b2/v1/models"
      if ($m2) {
        $altHit = $b2
        $models = $m2
        break
      }
    }
  }

  $results += [pscustomobject]@{
    port = $p
    base = $base
    v1 = $v1
    local_addresses = $localAddrs
    probed_alt_base = $altHit
    models_ok = [bool]$models
    models_count = if ($models -and $models.data) { $models.data.Count } else { 0 }
    health_ok = [bool]$health
    openapi_ok = [bool]$openapi
  }
}

$payload = [ordered]@{
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  host = $HostName
  timeout_sec = $TimeoutSec
  max_ports = $MaxPorts
  scanned_ports = $ports
  results = $results
}

$dir = Split-Path -Parent $OutPath
if ($dir -and !(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$payload | ConvertTo-Json -Depth 6 | Out-File -LiteralPath $OutPath -Encoding UTF8

Write-Host $OutPath
