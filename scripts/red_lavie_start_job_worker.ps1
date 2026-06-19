# Run ON Red LAVIE. Delegates to fleet_satellite_setup.ps1 (backward-compatible entry).
param(
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$Token = "",
    [string]$InstallRoot = "C:\clawstack_satellite",
    [int]$Port = 5682,
    [switch]$SkipScheduledTasks
)

$setup = Join-Path $PSScriptRoot "fleet_satellite_setup.ps1"
if (-not (Test-Path $setup)) {
    Invoke-WebRequest "$K10/fleet_satellite_setup.ps1" -OutFile $setup -UseBasicParsing
}

$args = @("-NodeId", "red_lavie", "-K10", $K10, "-Token", $Token)
if ($SkipScheduledTasks) { $args += "-SkipScheduledTasks" }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $setup @args
