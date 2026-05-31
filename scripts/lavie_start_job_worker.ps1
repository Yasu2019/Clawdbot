#Requires -Version 5.1
<#
.SYNOPSIS
  Start satellite job worker (SJP v1) on LAVIE/K3.

.DESCRIPTION
  Job artifacts default to E:\ or D:\clawstack_satellite\data\work\jobs (not C:).
  Override with SATELLITE_JOBS_ROOT in satellite .env or -JobsRoot.

.EXAMPLE
  .\scripts\lavie_start_job_worker.ps1 -AddFirewall
  .\scripts\lavie_start_job_worker.ps1 -InstallRoot C:\clawstack_satellite -JobsRoot D:\clawstack_satellite\data\work\jobs
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$JobsRoot = "",
    [int]$Port = 5680,
    [string]$NodeId = "lavie",
    [switch]$AddFirewall
)

$ErrorActionPreference = "Stop"

$DefaultJobsRootD = "D:\clawstack_satellite\data\work\jobs"
$DefaultJobsRootE = "E:\clawstack_satellite\data\work\jobs"
$DefaultJobsRootC = "C:\clawstack_satellite\data\work\jobs"

function Get-DefaultJobsRoot {
    if (Test-Path "D:\") { return $DefaultJobsRootD }
    if (Test-Path "E:\") { return $DefaultJobsRootE }
    return $DefaultJobsRootC
}

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$workerScript = Join-Path $RepoRoot "scripts\lavie_job_worker.py"
if (-not (Test-Path $workerScript)) {
    throw "Missing worker script: $workerScript"
}

$envPath = Join-Path $InstallRoot ".env"
if (-not (Test-Path $envPath)) {
    throw "Missing satellite .env: $envPath"
}

function Get-EnvValue {
    param([string]$Path, [string]$Key)
    foreach ($line in Get-Content $Path -Encoding UTF8) {
        $line = $line.Trim()
        if ($line.StartsWith("$Key=")) {
            return $line.Split("=", 2)[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Resolve-SatelliteJobsRoot {
    param(
        [string]$EnvPath,
        [string]$Override
    )
    if ($Override) {
        return $Override
    }
    $fromEnv = Get-EnvValue -Path $EnvPath -Key "SATELLITE_JOBS_ROOT"
    if ($fromEnv) {
        return $fromEnv
    }
    return Get-DefaultJobsRoot
}

function Ensure-EnvJobsRoot {
    param(
        [string]$EnvPath,
        [string]$JobsRootPath
    )
    $current = Get-EnvValue -Path $EnvPath -Key "SATELLITE_JOBS_ROOT"
    if ($current -eq $JobsRootPath) {
        return
    }
    if ($current) {
        Write-Host "[OK] SATELLITE_JOBS_ROOT already set: $current"
        return
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::AppendAllText($EnvPath, "`r`nSATELLITE_JOBS_ROOT=$JobsRootPath", $utf8)
    Write-Host "[OK] Wrote SATELLITE_JOBS_ROOT=$JobsRootPath to $EnvPath"
}

$token = Get-EnvValue -Path $envPath -Key "SATELLITE_JOB_TOKEN"
if (-not $token) {
    $token = [guid]::NewGuid().ToString("N")
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::AppendAllText($envPath, "`r`nSATELLITE_JOB_TOKEN=$token", $utf8)
    Write-Host "[OK] Generated SATELLITE_JOB_TOKEN in $envPath"
    Write-Host "[!!] Copy the same token to K10 repo .env: SATELLITE_JOB_TOKEN=$token"
}

$jobsRoot = Resolve-SatelliteJobsRoot -EnvPath $envPath -Override $JobsRoot
Ensure-EnvJobsRoot -EnvPath $envPath -JobsRootPath $jobsRoot
New-Item -ItemType Directory -Path $jobsRoot -Force | Out-Null

if ($AddFirewall) {
    $ruleName = "Clawstack satellite job worker $Port ($NodeId)"
    $existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
    if ($LASTEXITCODE -ne 0) {
        netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$Port profile=any | Out-Null
        Write-Host "[OK] Added firewall rule TCP $Port"
    } else {
        Write-Host "[OK] Firewall rule exists: $ruleName"
    }
}

$env:SATELLITE_INSTALL_ROOT = $InstallRoot
$env:SATELLITE_JOBS_ROOT = $jobsRoot
$env:SATELLITE_NODE_ID = $NodeId
$env:SATELLITE_JOB_TOKEN = $token

foreach ($key in @("CAE_DOCKER_CPUS", "CAE_DOCKER_MEMORY", "CAE_OPENRADIOSS_NTHREAD", "CAE_TE_WORKSPACE", "LAVIE_CAE_BOOST")) {
    $val = Get-EnvValue -Path $envPath -Key $key
    if ($val) {
        Set-Item -Path "env:$key" -Value $val
    }
}

Write-Host "[OK] jobs_root=$jobsRoot (Docker/n8n stay under $InstallRoot)"
Write-Host "[OK] Starting job worker on 0.0.0.0:$Port (Ctrl+C to stop)"
python $workerScript --bind 0.0.0.0 --port $Port --host $NodeId --jobs-root $jobsRoot
