param(
    [int]$Port = 8113,
    [switch]$NoStartup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Agent = Join-Path $Root "scripts\monitor_agent.py"
$Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
}
if (-not (Test-Path $Python)) {
    throw "Python not found"
}

$existing = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object {
        $_.CommandLine -match "monitor_agent.py" -and
        $_.CommandLine -match "MONITOR_AGENT_PORT=$Port"
    }
if (-not $existing) {
    $oldPort = $env:MONITOR_AGENT_PORT
    $oldUpload = $env:FLEET_EVIDENCE_UPLOAD
    try {
        $env:MONITOR_AGENT_PORT = [string]$Port
        $env:FLEET_EVIDENCE_UPLOAD = "0"
        $args = "`"$Agent`" MONITOR_AGENT_PORT=$Port"
        $proc = Start-Process -FilePath $Python -ArgumentList $args -WorkingDirectory $Root -WindowStyle Hidden -PassThru
        Write-Host "[OK] Fleet evidence receiver started PID=$($proc.Id) port=$Port"
    } finally {
        $env:MONITOR_AGENT_PORT = $oldPort
        $env:FLEET_EVIDENCE_UPLOAD = $oldUpload
    }
} else {
    Write-Host "[OK] Fleet evidence receiver already running PID=$($existing[0].ProcessId)"
}

if (-not $NoStartup) {
    $startup = [Environment]::GetFolderPath("Startup")
    New-Item -ItemType Directory -Force -Path $startup | Out-Null
    $vbs = Join-Path $startup "StartFleetEvidenceReceiver.vbs"
    $lines = @(
        'Set w = CreateObject("WScript.Shell")',
        'Set e = w.Environment("Process")',
        'e("MONITOR_AGENT_PORT") = "' + $Port + '"',
        'e("FLEET_EVIDENCE_UPLOAD") = "0"',
        'w.CurrentDirectory = "' + $Root + '"',
        'w.Run Chr(34) & "' + $Python + '" & Chr(34) & " " & Chr(34) & "' + $Agent + '" & Chr(34) & " MONITOR_AGENT_PORT=' + $Port + '", 0, False'
    )
    Set-Content -LiteralPath $vbs -Value $lines -Encoding ASCII
    Write-Host "[OK] Startup registered: $vbs"
}
