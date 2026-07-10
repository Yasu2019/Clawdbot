param(
    [int]$PollSeconds = 300,
    [switch]$NoStartup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "scripts\k10_fleet_idle_dispatch.py"
$PolicyPath = Join-Path $Root "data\workspace\fleet_idle_dispatch_policy.yaml"
$StartupDir = [Environment]::GetFolderPath("Startup")
$StartupVbs = Join-Path $StartupDir "StartFleetIdleDispatch.vbs"

if (-not (Test-Path $Script)) {
    throw "Script not found: $Script"
}

$Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    $Python = "python"
}

if (Test-Path $PolicyPath) {
    $policyText = Get-Content $PolicyPath -Raw
    if ($policyText -match 'poll_interval_sec:\s*(\d+)') {
        $PollSeconds = [int]$Matches[1]
    }
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -like "*k10_fleet_idle_dispatch.py*" -and
        $_.Name -match "^pythonw?\.exe$"
    }

if ($existing) {
    Write-Host "[OK] Fleet idle dispatch already running: PID=$($existing[0].ProcessId)"
} else {
    $Args = "`"$Script`" --poll-seconds $PollSeconds"
    $proc = Start-Process -FilePath $Python -ArgumentList $Args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Write-Host "[OK] Started fleet idle dispatch: PID=$($proc.Id) poll=${PollSeconds}s"
}

if (-not $NoStartup) {
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
    $vbs = @(
        'Set WshShell = CreateObject("WScript.Shell")',
        'WshShell.CurrentDirectory = "' + $Root + '"',
        'WshShell.Run """" + "' + $Python + '" + """" + " " + """" + "' + $Script + '" + """" + " --poll-seconds ' + $PollSeconds + '", 0, False'
    )
    Set-Content -Path $StartupVbs -Value $vbs -Encoding ASCII
    Write-Host "[OK] Startup registered: $StartupVbs"
}
