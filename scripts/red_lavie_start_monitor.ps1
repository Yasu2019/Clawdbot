# Run ON Red LAVIE. Minimal monitor_agent start (no nested powershell, PS 5.1 safe).
param(
    [string]$K10 = "http://100.119.18.40:8123",
    [string]$AgentPath = "C:\clawstack_satellite\scripts\monitor_agent.py"
)

$ErrorActionPreference = "Continue"

function Find-Pythonw {
    $candidates = @()
    try { $candidates += (& where.exe pythonw 2>$null) } catch {}
    $candidates += @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p) -and ($p -notmatch "\\WindowsApps\\")) { return $p }
    }
    return $null
}

Write-Host "=== Red LAVIE Monitor Start ==="
$pythonw = Find-Pythonw
if (-not $pythonw) { throw "pythonw.exe not found" }
Write-Host "Python: $pythonw"

$dir = Split-Path -Parent $AgentPath
New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "Download monitor_agent.py from K10..."
Invoke-WebRequest "$K10/monitor_agent.py" -OutFile $AgentPath -UseBasicParsing
if (-not (Test-Path $AgentPath)) { throw "download failed: $AgentPath" }
Write-Host "Saved: $AgentPath ($((Get-Item $AgentPath).Length) bytes)"

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -and ($_.CommandLine -match 'monitor_agent') } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Process -FilePath $pythonw -ArgumentList "`"$AgentPath`"" -WindowStyle Hidden
Start-Sleep -Seconds 8

$ok = $false
try {
    $r = Invoke-WebRequest "http://127.0.0.1:8111/metrics" -UseBasicParsing -TimeoutSec 5
    $ok = ($r.StatusCode -eq 200)
} catch {}

if ($ok) {
    Write-Host "RED_LAVIE_MONITOR_OK http://127.0.0.1:8111/metrics"
} else {
    Write-Host "[NG] metrics not responding. Debug with:"
    Write-Host "  & `"$($pythonw -replace 'pythonw','python')`" `"$AgentPath`""
    exit 1
}
