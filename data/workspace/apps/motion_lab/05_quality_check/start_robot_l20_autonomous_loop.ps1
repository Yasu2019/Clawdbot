$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..\..\..\..")).Path
$PythonScript = Join-Path $ScriptDir "run_robot_l20_autonomous_loop.py"
$LogDir = Join-Path $RepoRoot "data\workspace\apps\growth_dashboard"
$StdoutPath = Join-Path $LogDir "robot_l20_autonomous_loop_stdout.log"
$StderrPath = Join-Path $LogDir "robot_l20_autonomous_loop_stderr.log"

if (-not (Test-Path $PythonScript)) {
    throw "Missing autonomous loop script: $PythonScript"
}

$Args = @(
    $PythonScript,
    "--cycles", "200",
    "--sleep-sec", "60",
    "--count", "128",
    "--refine-top", "16",
    "--notify"
)

$proc = Start-Process -FilePath "python" -ArgumentList $Args -WorkingDirectory $RepoRoot -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath -WindowStyle Hidden -PassThru

$StatusPath = Join-Path $LogDir "robot_l20_autonomous_launcher_status.json"
$status = [ordered]@{
    schema = "clawstack.robot_l20_autonomous_launcher.v1"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    pid = $proc.Id
    cycles = 200
    sleep_sec = 60
    count = 128
    refine_top = 16
    stdout_log = $StdoutPath
    stderr_log = $StderrPath
    status = Join-Path $LogDir "robot_l20_autonomous_status.json"
}
$json = $status | ConvertTo-Json -Depth 4
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($StatusPath, $json, $utf8NoBom)
Write-Host ("Started robot L20 autonomous loop PID={0}" -f $proc.Id)
