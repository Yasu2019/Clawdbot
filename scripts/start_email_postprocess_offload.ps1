param(
    [int]$PollSeconds = 300,
    [switch]$NoStartup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "scripts\k10_fleet_idle_dispatch.py"
$Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
$StartupDir = [Environment]::GetFolderPath("Startup")
$StartupVbs = Join-Path $StartupDir "StartEmailPostprocessOffload.vbs"

$existing = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*k10_fleet_idle_dispatch.py*--email-offload-only*" -and
    $_.Name -match "^pythonw?(.exe)?$"
})
if ($existing.Count -gt 1) {
    $existing | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    $existing = @()
}
if ($existing.Count -eq 0) {
    $args = "`"$Script`" --email-offload-only --poll-seconds $PollSeconds"
    $proc = Start-Process -FilePath $Python -ArgumentList $args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Write-Host "[OK] Started email postprocess offload observer: PID=$($proc.Id)"
} else {
    Write-Host "[OK] Email postprocess offload already running: PID=$($existing[0].ProcessId)"
}

if (-not $NoStartup) {
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
    $command = '"' + $Python + '" "' + $Script + '" --email-offload-only --poll-seconds ' + $PollSeconds
    $vbs = @(
        'Set WshShell = CreateObject("WScript.Shell")',
        'WshShell.CurrentDirectory = "' + $Root + '"',
        'WshShell.Run "' + $command.Replace('"', '""') + '", 0, False'
    )
    Set-Content -Path $StartupVbs -Value $vbs -Encoding ASCII
    Write-Host "[OK] Startup registered: $StartupVbs"
}
