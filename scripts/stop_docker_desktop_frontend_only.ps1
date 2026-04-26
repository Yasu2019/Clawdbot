[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"

function Get-FrontendProcesses {
    Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
}

function Get-DashboardDockerCliProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "docker.exe" -and
        $_.CommandLine -like "* stats *" -and
        $_.CommandLine -like "*--all*" -and
        $_.CommandLine -like "*--no-stream*"
    }
}

function Test-DockerCliHealthy {
    try {
        & "C:\Program Files\Docker\Docker\resources\bin\docker.exe" version | Out-Null
        return $true
    } catch {
        return $false
    }
}

$status = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss K")
    stoppedProcessIds = @()
    dockerHealthyAfter = $false
    error = $null
}

try {
    $dashboardCli = Get-DashboardDockerCliProcesses
    foreach ($proc in $dashboardCli) {
        $status.stoppedProcessIds += $proc.ProcessId
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    }

    $frontends = Get-FrontendProcesses
    foreach ($proc in $frontends) {
        $status.stoppedProcessIds += $proc.Id
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    do {
        Start-Sleep -Milliseconds 500
        $remaining = Get-FrontendProcesses
        if (-not $remaining) {
            break
        }
    } while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds)

    $status.dockerHealthyAfter = Test-DockerCliHealthy
}
catch {
    $status.error = $_.Exception.Message
}

$status | ConvertTo-Json -Depth 6
