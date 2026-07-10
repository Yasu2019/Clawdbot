$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $Root "data\workspace\universal_growth_daemon.py"
$StartupDir = [Environment]::GetFolderPath("Startup")
$StartupVbs = Join-Path $StartupDir "StartUniversalGrowthDaemon.vbs"

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

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -like "*universal_growth_daemon.py*" -and
        $_.Name -match "^pythonw?\.exe$"
    }

# T056: 多重起動は全掃除。WATCHDOG_RESTART=1 で強制再起動。
$existing = @($existing)
if ($existing.Count -gt 1 -or ($existing.Count -ge 1 -and $env:WATCHDOG_RESTART -eq "1")) {
    Write-Host "T056 cleanup: stopping $($existing.Count) instance(s): $($existing.ProcessId -join ', ')"
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 3
    $existing = @()
}
if ($existing.Count -ge 1) {
    Write-Host "[OK] Universal Growth Daemon already running: PID=$($existing[0].ProcessId)"
} else {
    $Args = "`"$Script`""
    $proc = Start-Process -FilePath $Python -ArgumentList $Args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Write-Host "[OK] Started Universal Growth Daemon: PID=$($proc.Id)"
}

# Register Startup
New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
$vbs = @(
    'Set WshShell = CreateObject("WScript.Shell")',
    'WshShell.CurrentDirectory = "' + $Root + '"',
    'WshShell.Run """" + "' + $Python + '" + """" + " " + """" + "' + $Script + '" + """", 0, False'
)
Set-Content -Path $StartupVbs -Value $vbs -Encoding ASCII
Write-Host "[OK] Startup registered: $StartupVbs"
