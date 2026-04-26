$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = "python"
$scriptPath = Join-Path $repoRoot "data\workspace\watch_clawstack_unified_native_cutover_progress.py"
$statusPath = Join-Path $repoRoot "data\workspace\clawstack_unified_native_cutover_progress_watchdog_runner_status.json"
$stdoutPath = Join-Path $repoRoot "data\workspace\clawstack_unified_native_cutover_progress_watchdog.log"
$stderrPath = Join-Path $repoRoot "data\workspace\clawstack_unified_native_cutover_progress_watchdog.err.log"

$existing = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match '^python' -and $_.CommandLine -and $_.CommandLine -like "*watch_clawstack_unified_native_cutover_progress.py*"
}

if ($existing) {
  $status = [ordered]@{
    updatedAt = (Get-Date).ToString("s")
    ok = $true
    action = "already_running"
    pids = @($existing.ProcessId)
    scriptPath = $scriptPath
  }
  $status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
  Write-Output "already running: $($existing.ProcessId -join ', ')"
  exit 0
}

$proc = Start-Process -FilePath $python `
  -ArgumentList @($scriptPath) `
  -WorkingDirectory $repoRoot `
  -WindowStyle Hidden `
  -RedirectStandardOutput $stdoutPath `
  -RedirectStandardError $stderrPath `
  -PassThru

$status = [ordered]@{
  updatedAt = (Get-Date).ToString("s")
  ok = $true
  action = "started"
  pid = $proc.Id
  scriptPath = $scriptPath
  stdoutPath = $stdoutPath
  stderrPath = $stderrPath
}
$status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $statusPath -Encoding UTF8
Write-Output "started pid=$($proc.Id)"
