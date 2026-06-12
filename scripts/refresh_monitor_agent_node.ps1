# refresh_monitor_agent_node.ps1
# Download, restart, and verify monitor_agent.py on a Windows fleet node.
# This file is fetched by satellite workers from K10 to avoid long command lines.
param(
    [string]$K10Base = "http://100.119.18.40:8123",
    [string]$AgentPath = "C:\monitor_agent.py"
)

$ErrorActionPreference = "Stop"
$K10Base = $K10Base.TrimEnd("/")

function Test-UsablePython {
    param([string]$Path)
    if (-not $Path) { return $false }
    if ($Path -match "\\WindowsApps\\") { return $false }
    return Test-Path $Path
}

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
        if (Test-UsablePython $p) { return $p }
    }
    return ""
}

Write-Output "[1/5] find python"
$pythonw = Find-Python
if (-not $pythonw) { throw "python/pythonw not found" }
Write-Output "python=$pythonw"

Write-Output "[2/5] download latest monitor_agent"
(New-Object System.Net.WebClient).DownloadFile("$K10Base/monitor_agent.py", $AgentPath)
if (-not (Select-String -Path $AgentPath -Pattern "/diagnostics" -Quiet)) {
    throw "downloaded monitor_agent lacks diagnostics endpoint"
}

Write-Output "[3/5] stop old monitor_agent and port owner"
try {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match [regex]::Escape($AgentPath) } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
} catch {}

try {
    Get-NetTCPConnection -LocalPort 8111 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
} catch {}

try {
    netstat -ano |
        Select-String ":8111" |
        ForEach-Object {
            $parts = ($_.Line -split "\s+") | Where-Object { $_ }
            if ($parts.Length -ge 5 -and $parts[3] -eq "LISTENING") {
                $pidText = $parts[4]
                if ($pidText -match "^\d+$") {
                    Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
                    & taskkill.exe /PID $pidText /F | Out-Null
                }
            }
        }
    Start-Sleep -Seconds 2
} catch {}

try {
    Get-NetTCPConnection -LocalPort 8112 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
} catch {}

Write-Output "[4/5] start monitor_agent"
$env:NODE_DIAGNOSTIC_LOG = "1"
$env:NODE_DIAGNOSTIC_RETENTION_HOURS = "24"
$proc = Start-Process -FilePath $pythonw -ArgumentList "`"$AgentPath`"" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
Write-Output "pid=$($proc.Id)"

Write-Output "[5/5] register startup and verify"
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
$vbsPath = Join-Path $startupDir "StartMonitorAgent.vbs"
$line1 = 'Set w = CreateObject("WScript.Shell")'
$line2 = 'w.Run Chr(34) & "' + $pythonw + '" & Chr(34) & " " & Chr(34) & "' + $AgentPath + '" & Chr(34), 0, False'
Set-Content -Path $vbsPath -Value $line1 -Encoding ASCII
Add-Content -Path $vbsPath -Value $line2 -Encoding ASCII
Write-Output "startup=$vbsPath"

$metricsOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $metrics = Invoke-WebRequest "http://127.0.0.1:8111/metrics" -UseBasicParsing -TimeoutSec 3
        if ($metrics.StatusCode -eq 200) {
            $metricsOk = $true
            Write-Output "metrics_status=$($metrics.StatusCode)"
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $metricsOk) { throw "metrics endpoint did not become ready" }

$diagOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $diag = Invoke-WebRequest "http://127.0.0.1:8111/diagnostics" -UseBasicParsing -TimeoutSec 3
        if ($diag.StatusCode -eq 200) {
            $diagOk = $true
            Write-Output "diagnostics_status=$($diag.StatusCode)"
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}
if ($diagOk) {
    Write-Output "DIAGNOSTICS_READY"
    exit 0
}

Write-Output "[WARN] 8111 diagnostics unavailable; starting diagnostics fallback on 8112"
$altPort = "8112"
$cmdArgs = '/c set "MONITOR_AGENT_PORT=' + $altPort + '"&& set "NODE_DIAGNOSTIC_LOG=1"&& set "NODE_DIAGNOSTIC_RETENTION_HOURS=24"&& "' + $pythonw + '" "' + $AgentPath + '"'
$altProc = Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
Write-Output "alt_pid=$($altProc.Id)"

$altVbsPath = Join-Path $startupDir "StartMonitorAgentDiagnostics.vbs"
$altLine1 = 'Set w = CreateObject("WScript.Shell")'
$altLine2 = 'Set env = w.Environment("PROCESS")'
$altLine3 = 'env("MONITOR_AGENT_PORT") = "8112"'
$altLine4 = 'env("NODE_DIAGNOSTIC_LOG") = "1"'
$altLine5 = 'env("NODE_DIAGNOSTIC_RETENTION_HOURS") = "24"'
$altLine6 = 'w.Run Chr(34) & "' + $pythonw + '" & Chr(34) & " " & Chr(34) & "' + $AgentPath + '" & Chr(34), 0, False'
Set-Content -Path $altVbsPath -Value $altLine1 -Encoding ASCII
Add-Content -Path $altVbsPath -Value $altLine2 -Encoding ASCII
Add-Content -Path $altVbsPath -Value $altLine3 -Encoding ASCII
Add-Content -Path $altVbsPath -Value $altLine4 -Encoding ASCII
Add-Content -Path $altVbsPath -Value $altLine5 -Encoding ASCII
Add-Content -Path $altVbsPath -Value $altLine6 -Encoding ASCII
Write-Output "alt_startup=$altVbsPath"

$altDiagOk = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $altDiag = Invoke-WebRequest "http://127.0.0.1:8112/diagnostics" -UseBasicParsing -TimeoutSec 3
        if ($altDiag.StatusCode -eq 200) {
            $altDiagOk = $true
            Write-Output "diagnostics_alt_status=$($altDiag.StatusCode)"
            break
        }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $altDiagOk) { throw "diagnostics endpoint did not become ready on 8111 or 8112" }

Write-Output "DIAGNOSTICS_READY_ALT"
