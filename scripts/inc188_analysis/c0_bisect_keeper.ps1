# INC-188: keep c0_bisect_frames.sh alive (restart after sign-out / crash). ASCII only (PS 5.1).
# Does nothing when the bisection is DONE, when an ALARM_c0_bisect.txt exists (needs a human),
# or when an instance is already running.
$ws    = "D:\Clawdbot_Docker_20260125\data\workspace"
$state = Join-Path $ws "c0_bisect_state.txt"
$alarm = Join-Path $ws "ALARM_c0_bisect.txt"
$log   = Join-Path $ws "c0_bisect_log.txt"
if (-not (Test-Path -LiteralPath $state)) { exit 0 }
if ((Get-Content -LiteralPath $state) -match "^DONE=1") { exit 0 }
if (Test-Path -LiteralPath $alarm) { exit 0 }
$alive = @(Get-CimInstance Win32_Process -Filter "Name='bash.exe'" | Where-Object { $_.CommandLine -like "*c0_bisect_frames.sh*" })
if ($alive.Count -gt 0) { exit 0 }
$cmd = '"C:\Program Files\Git\bin\bash.exe" -lc "bash D:/Clawdbot_Docker_20260125/scripts/inc188_analysis/c0_bisect_frames.sh"'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "D:\Clawdbot_Docker_20260125" }
Add-Content -LiteralPath $log -Value ((Get-Date -Format "MM-dd HH:mm:ss") + " keeper: controller was not running, restarted pid " + $r.ProcessId) -Encoding ASCII
exit 0
