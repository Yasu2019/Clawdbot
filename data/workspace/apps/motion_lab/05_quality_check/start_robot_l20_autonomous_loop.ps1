param(
    [int]$SeedBase = 20260620,
    [int]$BatchNumber = 1
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..\..\..\..")).Path
$PythonScript = Join-Path $ScriptDir "run_robot_l20_autonomous_loop.py"
$LogDir = Join-Path $RepoRoot "data\workspace\apps\growth_dashboard"
$StdoutPath = Join-Path $LogDir "robot_l20_autonomous_loop_stdout.log"
$StderrPath = Join-Path $LogDir "robot_l20_autonomous_loop_stderr.log"
$LauncherPath = Join-Path $LogDir "robot_l20_autonomous_launcher_status.json"

if (-not (Test-Path $PythonScript)) {
    throw "Missing autonomous loop script: $PythonScript"
}

if (Test-Path $LauncherPath) {
    try {
        $launcher = Get-Content $LauncherPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $loopPid = [int]$launcher.pid
        if ($loopPid -gt 0) {
            $alive = Get-Process -Id $loopPid -ErrorAction SilentlyContinue
            if ($alive -and ($alive.Name -like "*python*")) {
                Write-Host "[OK] Robot L20 loop already running PID=$loopPid batch=$($launcher.batch_number)"
                exit 0
            }
        }
    } catch { }
}

$Args = @(
    $PythonScript,
    "--cycles", "200",
    "--sleep-sec", "60",
    "--count", "128",
    "--refine-top", "16",
    "--seed-base", "$SeedBase",
    "--batch-number", "$BatchNumber",
    "--notify"
)

$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }
$proc = Start-Process -FilePath $PythonExe -ArgumentList $Args -WorkingDirectory $RepoRoot -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath -WindowStyle Hidden -PassThru

$status = [ordered]@{
    schema = "clawstack.robot_l20_autonomous_launcher.v1"
    started_at = (Get-Date).ToUniversalTime().ToString("o")
    pid = $proc.Id
    batch_number = $BatchNumber
    seed_base = $SeedBase
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
[System.IO.File]::WriteAllText($LauncherPath, $json, $utf8NoBom)
Write-Host ("Started robot L20 autonomous loop PID={0} batch={1} seed={2}" -f $proc.Id, $BatchNumber, $SeedBase)
