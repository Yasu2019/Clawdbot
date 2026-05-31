#Requires -Version 5.1
<#
.SYNOPSIS
  Apply CAE performance boost settings on LAVIE (power plan + CAE docker limits).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File C:\lavie_usb_pack\scripts\lavie_boost_apply.ps1
#>
[CmdletBinding()]
param(
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$RepoRoot = "",
    [int]$DockerCpus = 6,
    [string]$DockerMemory = "8g",
    [int]$OpenRadiossThreads = 4
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

function Set-EnvKey {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    $lines = @()
    if (Test-Path $Path) {
        $lines = Get-Content $Path -Encoding UTF8
    }
    $found = $false
    $out = foreach ($line in $lines) {
        if ($line.Trim().StartsWith("$Key=")) {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) {
        $out += "$Key=$Value"
    }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, ($out -join "`r`n") + "`r`n", $utf8)
}

Write-Host "[boost] Applying LAVIE CAE boost settings..."

$highPerf = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
$ultimate = "e9a42b02-d5df-448d-aa00-03f14749ebe6"
$active = $highPerf
try {
    powercfg /setactive $ultimate 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $active = $ultimate
        Write-Host "[OK] Power plan: Ultimate Performance"
    } else {
        powercfg /setactive $highPerf | Out-Null
        Write-Host "[OK] Power plan: High performance"
    }
} catch {
    Write-Host "[!!] powercfg skipped (run as Admin for best results)"
}

foreach ($path in @(
    (Join-Path $InstallRoot ".env"),
    (Join-Path $RepoRoot ".env")
)) {
    if (-not (Test-Path $path)) { continue }
    Set-EnvKey -Path $path -Key "CAE_DOCKER_CPUS" -Value $DockerCpus
    Set-EnvKey -Path $path -Key "CAE_DOCKER_MEMORY" -Value $DockerMemory
    Set-EnvKey -Path $path -Key "CAE_OPENRADIOSS_NTHREAD" -Value $OpenRadiossThreads
    Set-EnvKey -Path $path -Key "LAVIE_CAE_BOOST" -Value "1"
    Set-EnvKey -Path $path -Key "CAE_TE_WORKSPACE" -Value "E:/clawstack_satellite/data/work/cae_te_workspace"
    Write-Host "[OK] Updated $path"
}

Write-Host "[OK] Boost applied: cpus=$DockerCpus memory=$DockerMemory or_threads=$OpenRadiossThreads"
Write-Host "[!!] Docker Desktop: Settings -> Resources -> CPUs 6+ / Memory 24GB+ recommended"
