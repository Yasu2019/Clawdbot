param(
    [int]$PollSeconds = 240,
    [switch]$NoStartup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "scripts\k10_red_lavie_continuous_loop.py"
$Workspace = Join-Path $Root "data\workspace"
$StatusPath = Join-Path $Workspace "red_lavie_continuous_loop_status.json"
$StartupDir = [Environment]::GetFolderPath("Startup")
$StartupVbs = Join-Path $StartupDir "StartRedLavieContinuousLoop.vbs"

if (-not (Test-Path $Script)) {
    throw "Loop script not found: $Script"
}

$Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -like "*k10_red_lavie_continuous_loop.py*" -and
        $_.Name -match "^pythonw?\.exe$"
    }

if ($existing) {
    Write-Host "[OK] Red LAVIE continuous loop already running: PID=$($existing[0].ProcessId)"
} else {
    New-Item -ItemType Directory -Force -Path $Workspace | Out-Null
    $Args = "`"$Script`" --poll-seconds $PollSeconds"
    $proc = Start-Process -FilePath $Python -ArgumentList $Args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Write-Host "[OK] Started Red LAVIE non-CAE offload loop: PID=$($proc.Id)"
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

if (Test-Path $StatusPath) {
    Write-Host "[OK] Status: $StatusPath"
} else {
    Write-Host "[WARN] Status will be created after the first loop cycle: $StatusPath"
}
