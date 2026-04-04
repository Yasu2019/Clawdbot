[CmdletBinding()]
param(
    [string]$ProjectRoot = "D:\Clawdbot_Docker_20260125",
    [int]$DockerReadyTimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"

function Write-StatusJson {
    param(
        [string]$Path,
        [hashtable]$Data
    )
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $Data | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds = 30,
        [int]$PollMilliseconds = 500
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (& $Condition) {
            return $true
        }
        Start-Sleep -Milliseconds $PollMilliseconds
    }
    return $false
}

function Stop-DockerDesktopProcesses {
    param(
        [int]$TimeoutSeconds = 20
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    do {
        $front = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
        $back = Get-Process "com.docker.backend" -ErrorAction SilentlyContinue
        if (-not $front -and -not $back) {
            Start-Sleep -Milliseconds 1200
            $front = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
            $back = Get-Process "com.docker.backend" -ErrorAction SilentlyContinue
            if (-not $front -and -not $back) {
                return $true
            }
        }
        if ($front) {
            $front | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        if ($back) {
            $back | Stop-Process -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 700
    } while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds)
    return $false
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$statusPath = Join-Path $ProjectRoot "data\workspace\docker_desktop_frontend_cache_reset_status_$timestamp.json"
$backupRoot = Join-Path $ProjectRoot "backups\docker_desktop_frontend_reset\$timestamp"
$profileRoot = Join-Path $env:APPDATA "Docker Desktop"
$dockerFrontend = "C:\Program Files\Docker\Docker\frontend\Docker Desktop.exe"
$dockerCli = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"

$targets = @(
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "Local Storage",
    "Session Storage",
    "Network",
    "blob_storage",
    "window-management.json",
    "persisted-state.json",
    "Preferences",
    "lockfile",
    "DIPS",
    "DIPS-wal"
)

$status = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    profileRoot = $profileRoot
    dockerFrontend = $dockerFrontend
    dockerCli = $dockerCli
    backupRoot = $backupRoot
    targets = $targets
    backupItems = @()
    removedItems = @()
    frontendStopped = $false
    backendStopped = $false
    frontendRestarted = $false
    dockerReady = $false
    dockerVersion = $null
    statsProbe = $null
    error = $null
}

try {
    if (-not (Test-Path $profileRoot)) {
        throw "Docker Desktop profile not found: $profileRoot"
    }
    if (-not (Test-Path $dockerFrontend)) {
        throw "Docker Desktop frontend executable not found: $dockerFrontend"
    }
    if (-not (Test-Path $dockerCli)) {
        throw "docker.exe not found: $dockerCli"
    }

    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

    $status.frontendStopped = $true
    $status.backendStopped = $true
    if (-not (Stop-DockerDesktopProcesses -TimeoutSeconds 25)) {
        throw "Docker Desktop frontend/backend processes could not be fully stopped for cache reset."
    }

    foreach ($target in $targets) {
        $source = Join-Path $profileRoot $target
        if (-not (Test-Path $source)) {
            continue
        }
        $destination = Join-Path $backupRoot $target
        $parent = Split-Path -Parent $destination
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Move-Item -LiteralPath $source -Destination $destination -Force
        $status.backupItems += $target
    }

    Start-Process -FilePath $dockerFrontend
    $status.frontendRestarted = $true

    $dockerReady = Wait-Until -TimeoutSeconds $DockerReadyTimeoutSeconds -PollMilliseconds 1500 -Condition {
        try {
            & $dockerCli version | Out-Null
            return $true
        } catch {
            return $false
        }
    }
    $status.dockerReady = $dockerReady

    try {
        $status.dockerVersion = (& $dockerCli version --format '{{json .Server}}' 2>&1 | Out-String).Trim()
    } catch {
        $status.dockerVersion = $_.Exception.Message
    }

    try {
        $status.statsProbe = (& $dockerCli stats --all --no-trunc --no-stream --format '{{json .}}' 2>&1 | Select-Object -First 3 | Out-String).Trim()
    } catch {
        $status.statsProbe = $_.Exception.Message
    }
}
catch {
    $status.error = $_.Exception.Message
}
finally {
    Write-StatusJson -Path $statusPath -Data $status
    Write-Output "Status: $statusPath"
    if ($status.error) {
        Write-Error $status.error
    }
}
