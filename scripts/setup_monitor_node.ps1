# setup_monitor_node.ps1
# Deploy and start monitor_agent.py on a Windows fleet node.
# Compatible with Windows PowerShell 5.0-era hosts. Run as a normal user.
param(
    [string]$K10Url = "http://100.119.18.40:8123/monitor_agent.py",
    [string]$AgentPath = "C:\monitor_agent.py"
)

$ErrorActionPreference = "SilentlyContinue"

function Test-UsablePython {
    param([string]$Path)
    if (-not $Path) { return $false }
    if ($Path -match "\\WindowsApps\\") { return $false }
    return Test-Path $Path
}

Write-Host "=== Clawstack Monitor Agent Setup ==="
Write-Host "Hostname: $env:COMPUTERNAME"
Write-Host "K10 Source: $K10Url"
Write-Host ""

# [1/4] Find a real Python executable. WindowsApps aliases are not valid for startup.
Write-Host "[1/4] Finding Python..."
$pythonw = $null
try {
    $found = & where.exe pythonw 2>$null
    foreach ($p in $found) {
        if (Test-UsablePython $p) { $pythonw = $p; break }
    }
} catch {}

if (-not $pythonw) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe",
        "C:\Python313\pythonw.exe",
        "C:\Python312\pythonw.exe",
        "C:\Python311\pythonw.exe",
        "C:\Python310\pythonw.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $pythonw = $c; break }
    }
}

if (-not $pythonw) {
    try {
        $foundPy = & where.exe python 2>$null
        foreach ($p in $foundPy) {
            if (Test-UsablePython $p) { $pythonw = $p; break }
        }
    } catch {}
}

if (-not $pythonw) {
    Write-Host "  [ERROR] pythonw.exe/python.exe was not found. Install Python and retry."
    exit 1
}
Write-Host "  -> Python: $pythonw"

# [2/4] Stop an existing monitor agent only after a usable Python was found.
Write-Host "[2/4] Stopping existing agent..."
try {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'monitor_agent' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
} catch {}

# [3/4] Download monitor_agent.py. WebClient works on older Windows hosts.
Write-Host "[3/4] Downloading monitor_agent.py..."
try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($K10Url, $AgentPath)
    Write-Host "  -> Saved to $AgentPath"
} catch {
    Write-Host "  [ERROR] Download failed: $_"
    Write-Host "  Verify that K10 is serving $K10Url."
    exit 1
}

# [4/4] Start now and register Startup VBS.
Write-Host "[4/4] Starting and registering startup..."

$proc = Start-Process -FilePath $pythonw -ArgumentList "`"$AgentPath`"" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 2

if ($proc -and -not $proc.HasExited) {
    Write-Host "  -> Started PID=$($proc.Id)"
} else {
    Write-Host "  [WARN] Process may have exited. Checking port..."
}

$metricsOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $resp = Invoke-WebRequest "http://127.0.0.1:8111/metrics" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $metricsOk = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}

if ($metricsOk) {
    Write-Host "  -> Metrics OK: http://localhost:8111/metrics"
} else {
    Write-Host "  [WARN] Metrics did not respond within 10 seconds."
}

# Startup VBS. ASCII encoding is required for old Windows hosts.
$vbsPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\StartMonitorAgent.vbs"
$vbsDir = Split-Path -Parent $vbsPath
if (-not (Test-Path $vbsDir)) {
    New-Item -ItemType Directory -Path $vbsDir -Force | Out-Null
}
$line1 = 'Set w = CreateObject("WScript.Shell")'
$line2 = 'w.Run Chr(34) & "' + $pythonw + '" & Chr(34) & " " & Chr(34) & "' + $AgentPath + '" & Chr(34), 0, False'
Set-Content -Path $vbsPath -Value $line1 -Encoding ASCII
Add-Content -Path $vbsPath -Value $line2 -Encoding ASCII
Write-Host "  -> Startup VBS: $vbsPath"

Write-Host ""
Write-Host "=== Setup Complete ==="
Write-Host "Metrics: http://localhost:8111/metrics"
