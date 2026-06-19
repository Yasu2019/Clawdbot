# lhm_setup.ps1 -- LibreHardwareMonitor install + start (satellite nodes, no local repo)
$ErrorActionPreference = 'SilentlyContinue'
$d = 'C:\LibreHardwareMonitor'
$t = "$d\LibreHardwareMonitor.exe"
$K10 = 'http://100.119.18.40:8123'
$cfgDir = Join-Path $env:APPDATA 'LibreHardwareMonitor'
$cfg = Join-Path $cfgDir 'LibreHardwareMonitor.config'

function Test-LhmHttp {
    try {
        $r = Invoke-WebRequest 'http://127.0.0.1:8085/data.json' -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

if (Test-LhmHttp) {
    Write-Host '[OK] LHM Remote Web Server already on :8085'
    exit 0
}

if (-not (Test-Path $d)) { New-Item -ItemType Directory $d -Force | Out-Null }

if (-not (Test-Path $t)) {
    Write-Host '[1/3] Download LibreHardwareMonitor...'
    $z = "$env:TEMP\lhm.zip"
    try {
        Invoke-WebRequest -Uri "$K10/LibreHardwareMonitor.zip" -OutFile $z -UseBasicParsing -TimeoutSec 120
    } catch {
        Write-Host "  K10 zip failed, trying GitHub..."
        Invoke-WebRequest -Uri 'https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest/download/LibreHardwareMonitor.zip' `
            -OutFile $z -UseBasicParsing -TimeoutSec 120
    }
    if (Test-Path $z) {
        Expand-Archive $z $d -Force
        Remove-Item $z -Force -ErrorAction SilentlyContinue
        $e = (Get-ChildItem $d -Filter 'LibreHardwareMonitor.exe' -Recurse | Select-Object -First 1).FullName
        if ($e -and $e -ne $t) { Copy-Item $e $t -Force }
    }
}

if (-not (Test-Path $t)) {
    Write-Host '[ERROR] LibreHardwareMonitor.exe not found under C:\LibreHardwareMonitor'
    exit 1
}

Write-Host '[2/3] Enable Remote Web Server config and start LibreHardwareMonitor...'
if (-not (Test-Path $cfgDir)) { New-Item -ItemType Directory $cfgDir -Force | Out-Null }
$json = @"
{
    "IsHttpServerEnabled": true,
    "MinimizeToTray": true,
    "HttpPort": 8085
}
"@
Set-Content -Path $cfg -Value $json -Encoding UTF8

# Also write to system profile AppData just in case it runs under SYSTEM account later
$sysCfgDir = "C:\Windows\System32\config\systemprofile\AppData\Roaming\LibreHardwareMonitor"
try {
    if (-not (Test-Path $sysCfgDir)) { New-Item -ItemType Directory $sysCfgDir -Force | Out-Null }
    Set-Content -Path (Join-Path $sysCfgDir 'LibreHardwareMonitor.config') -Value $json -Encoding UTF8
} catch {}

$a  = New-ScheduledTaskAction -Execute $t
$tr = New-ScheduledTaskTrigger -AtLogOn
$s  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$p  = New-ScheduledTaskPrincipal -GroupId "BUILTIN\Administrators" -RunLevel Highest
Register-ScheduledTask -TaskName 'LibreHardwareMonitor' -Action $a -Trigger $tr -Principal $p -Settings $s -Force | Out-Null

Get-Process -Name LibreHardwareMonitor -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process $t -WindowStyle Minimized
Start-Sleep -Seconds 4

Write-Host '[3/3] Verify Remote Web Server...'

if (Test-LhmHttp) {
    Write-Host '[OK] Remote Web Server is UP'
    exit 0
}
Write-Host '[WAIT] :8085 not listening yet'
Write-Host '  If needed: LHM window -> Options -> Remote Web Server -> Run'
exit 2
