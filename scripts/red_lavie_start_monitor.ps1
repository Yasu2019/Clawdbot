# Run ON Red LAVIE. Delegates to fleet_satellite_setup.ps1 (monitor only).
param(
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$InstallRoot = "C:\clawstack_satellite",
    [string]$AgentPath = "",
    [int]$Port = 8111,
    [switch]$SkipScheduledTasks
)

$setup = Join-Path $PSScriptRoot "fleet_satellite_setup.ps1"
if (-not (Test-Path $setup)) {
    Invoke-WebRequest "$K10/fleet_satellite_setup.ps1" -OutFile $setup -UseBasicParsing
}

$args = @("-NodeId", "red_lavie", "-K10", $K10, "-SkipWorker")
if ($SkipScheduledTasks) { $args += "-SkipScheduledTasks" }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup @args
