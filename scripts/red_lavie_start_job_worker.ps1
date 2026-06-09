# Start Red LAVIE satellite job worker on port 5682.
# This script is downloaded from K10 and run once on Red LAVIE.
param(
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$Token = "",
    [string]$InstallRoot = "C:\clawstack_satellite",
    [int]$Port = 5682
)

$ErrorActionPreference = "Stop"

function Find-Python {
    $candidates = @()
    try { $candidates += (& where.exe pythonw 2>$null) } catch {}
    try { $candidates += (& where.exe python 2>$null) } catch {}
    $candidates += @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe",
        "C:\Python313\pythonw.exe",
        "C:\Python312\pythonw.exe",
        "C:\Python311\pythonw.exe",
        "C:\Python310\pythonw.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p) -and ($p -notmatch "\\WindowsApps\\")) {
            return $p
        }
    }
    return ""
}

if (-not $Token) {
    throw "Token is required. Pass -Token from K10."
}

$scriptsDir = Join-Path $InstallRoot "scripts"
$jobsRoot = Join-Path $InstallRoot "data\work\jobs"
$logsDir = Join-Path $InstallRoot "logs"
New-Item -ItemType Directory -Force -Path $scriptsDir, $jobsRoot, $logsDir | Out-Null

$workerPath = Join-Path $scriptsDir "lavie_job_worker.py"
$envPath = Join-Path $InstallRoot ".env"
$logPath = Join-Path $logsDir "red_lavie_job_worker.log"

Write-Host "=== Red LAVIE Job Worker Setup ==="
Write-Host "InstallRoot: $InstallRoot"
Write-Host "Port: $Port"

$pythonw = Find-Python
if (-not $pythonw) {
    throw "python/pythonw was not found. Install Python and retry."
}
Write-Host "Python: $pythonw"

Write-Host "[1/5] Download worker..."
(New-Object System.Net.WebClient).DownloadFile("$K10/lavie_job_worker.py", $workerPath)

Write-Host "[2/5] Write env..."
@(
    "SATELLITE_JOB_TOKEN=$Token",
    "SATELLITE_NODE_ID=red_lavie",
    "SATELLITE_INSTALL_ROOT=$InstallRoot",
    "SATELLITE_JOBS_ROOT=$jobsRoot",
    "SATELLITE_REPO_ROOT=C:\lavie_usb_pack",
    "CAE_TE_WORKSPACE=$InstallRoot\data\work\cae_te_workspace",
    "LOCAL_MONITOR_METRICS_URL=http://127.0.0.1:8111/metrics"
) | Set-Content -Path $envPath -Encoding ASCII

Write-Host "[3/5] Stop existing worker..."
try {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "lavie_job_worker.py" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
} catch {}

Write-Host "[4/5] Open firewall and start worker..."
try {
    New-NetFirewallRule -DisplayName "Clawstack Red LAVIE Job Worker 5682" -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
} catch {
    Write-Host "[WARN] Firewall rule was not created. If needed, rerun PowerShell as Administrator."
}

$argsLine = "`"$workerPath`" --bind 0.0.0.0 --port $Port --host red_lavie --jobs-root `"$jobsRoot`""
$proc = Start-Process -FilePath $pythonw -ArgumentList $argsLine -WorkingDirectory $scriptsDir -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2
Write-Host "Started PID=$($proc.Id)"

Write-Host "[5/5] Register startup..."
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
$vbsPath = Join-Path $startupDir "StartRedLavieJobWorker.vbs"
$line1 = 'Set w = CreateObject("WScript.Shell")'
$line2 = 'w.CurrentDirectory = "' + $scriptsDir + '"'
$line3 = 'w.Run Chr(34) & "' + $pythonw + '" & Chr(34) & " ' + $argsLine.Replace('"', '""') + '", 0, False'
Set-Content -Path $vbsPath -Value $line1 -Encoding ASCII
Add-Content -Path $vbsPath -Value $line2 -Encoding ASCII
Add-Content -Path $vbsPath -Value $line3 -Encoding ASCII
Write-Host "Startup VBS: $vbsPath"

$ok = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:$Port/healthz" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) {
            $ok = $true
            Write-Host "Health OK: $($r.Content)"
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $ok) {
    throw "Worker did not respond on http://127.0.0.1:$Port/healthz"
}

Write-Host "=== Setup Complete ==="
Write-Host "Worker: http://localhost:$Port/healthz"
