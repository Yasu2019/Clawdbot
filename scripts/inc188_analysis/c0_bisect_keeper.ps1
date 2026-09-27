# INC-188 keeper (task INC188_C0Bisect_Keeper, every 10 min). ASCII only (PS 5.1).
# Restarts detached helper loops after sign-out / crash:
#   1. c0_bisect_frames.sh  - unless the bisection is DONE, ALARM_c0_bisect.txt exists, or it is running
#   2. frame_monitor.sh     - unless data\workspace\frame_monitor.disabled exists or it is running
#   3. engine_mem_log.sh    - unless it is running
# NOTE: "running" = any bash.exe whose command line contains the script name. Do not test this
# from a Bash tool call whose own command line contains that name (it counts as running).
$ws  = "D:\Clawdbot_Docker_20260125\data\workspace"
$log = Join-Path $ws "c0_bisect_log.txt"
$bash = "C:\Program Files\Git\bin\bash.exe"

function Start-Detached([string]$script, [string]$logFile, [string]$what) {
  $cmd = '"' + $bash + '" -lc "bash D:/Clawdbot_Docker_20260125/scripts/inc188_analysis/' + $script + '"'
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "D:\Clawdbot_Docker_20260125" }
  Add-Content -LiteralPath $logFile -Value ((Get-Date -Format "MM-dd HH:mm:ss") + " keeper: " + $what + " was not running, restarted pid " + $r.ProcessId) -Encoding ASCII
}

function Test-Alive([string]$script) {
  return @(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object { $_.CommandLine -like ("*" + $script + "*") }).Count -gt 0
}

# 1. C0 bisection
$state = Join-Path $ws "c0_bisect_state.txt"
if ((Test-Path -LiteralPath $state) -and -not ((Get-Content -LiteralPath $state) -match "^DONE=1") -and
    -not (Test-Path -LiteralPath (Join-Path $ws "ALARM_c0_bisect.txt")) -and -not (Test-Alive "c0_bisect_frames.sh")) {
  Start-Detached "c0_bisect_frames.sh" $log "c0_bisect_frames.sh"
}

# 2. per-frame round-hole monitor
if (-not (Test-Path -LiteralPath (Join-Path $ws "frame_monitor.disabled")) -and -not (Test-Alive "frame_monitor.sh")) {
  Start-Detached "frame_monitor.sh" (Join-Path $ws "frame_monitor_log.txt") "frame_monitor.sh"
}

# 3. engine memory logger (RSS vs simulated time, feeds the memory-cap tuning)
if (-not (Test-Alive "engine_mem_log.sh")) {
  Start-Detached "engine_mem_log.sh" (Join-Path $ws "frame_monitor_log.txt") "engine_mem_log.sh"
}
exit 0
