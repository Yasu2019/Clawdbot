[CmdletBinding()]
param(
    [string]$Distro = '',
    [string]$Unit = '',
    [string]$CaseDir = '',
    [int]$BudgetSeconds = 3600,
    [int]$Ranks = 2,
    [string]$EndTime = '0.001',
    [string]$LogName = 'log.preflight',
    [string]$Runner = '/usr/local/sbin/run_openfoam14_box_preflight_guarded_v3.sh',
    [string]$ManifestPath = '',
    [switch]$ValidateOnly,
    [string]$WorkerConfigBase64 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-LaunchManifest([object]$Record, [switch]$CreateOnly) {
    $parent = Split-Path -Parent $ManifestPath
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $writeToken = [guid]::NewGuid().ToString('N')
    $temporaryPath = "$ManifestPath.$writeToken.tmp"
    $backupPath = "$ManifestPath.$writeToken.bak"
    try {
        $json = $Record | ConvertTo-Json -Depth 6
        Set-Content -LiteralPath $temporaryPath -Value $json -Encoding UTF8
        if (Test-Path -LiteralPath $ManifestPath) {
            if ($CreateOnly) {
                throw "Refusing to overwrite existing launch manifest: $ManifestPath"
            }
            [System.IO.File]::Replace($temporaryPath, $ManifestPath, $backupPath)
            if (Test-Path -LiteralPath $backupPath) { Remove-Item -LiteralPath $backupPath -Force }
        }
        else {
            [System.IO.File]::Move($temporaryPath, $ManifestPath)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
        if (Test-Path -LiteralPath $backupPath) {
            Remove-Item -LiteralPath $backupPath -Force
        }
    }
}

function Invoke-WithLaunchMutex([scriptblock]$Action, [int]$TimeoutSeconds = 120) {
    $mutex = [System.Threading.Mutex]::new($false, 'Global\Clawstack.OpenFOAM.Launch.v1')
    $acquired = $false
    try {
        try {
            $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds($TimeoutSeconds))
        }
        catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
        }
        if (-not $acquired) {
            throw "Timed out after ${TimeoutSeconds}s waiting to update the OpenFOAM launch manifest"
        }
        & $Action
    }
    finally {
        if ($acquired) { $mutex.ReleaseMutex() }
        $mutex.Dispose()
    }
}

function Remove-OwnedKeepaliveTask([string]$TaskName, [string]$ExpectedWorkerConfigBase64) {
    # A random task name reduces collision risk, but cleanup must also verify
    # the registered action fingerprint before deleting anything by name.
    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath '\' -ErrorAction SilentlyContinue
    if (-not $task -or $task.Actions.Count -ne 1) { return $false }
    $expectedArgument = "-WorkerConfigBase64 $ExpectedWorkerConfigBase64"
    if (-not $task.Actions[0].Arguments.Contains($expectedArgument)) { return $false }
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath '\' -Confirm:$false -ErrorAction Stop | Out-Null
    return $true
}

function New-KeepaliveScript([string]$Unit, [string]$CaseDir, [string]$ReadyPath) {
    # Worker task arguments contain validated scalar values only; shell code
    # is reconstructed from this fixed template, never accepted from Base64.
    $keepaliveTemplate = @'
unit='__UNIT__'
case_dir='__CASE_DIR__'
ready='__READY__'
trap 'rm -f -- "$ready"' EXIT
printf '%s\n' "$$" > "$ready"
report_terminal_result() {
    local stop_reason attempt terminal_facts
    local solver_exit_code checkpoint_valid latest_time fatal_count
    terminal_facts=''
    for attempt in 1 2 3 4 5; do
        terminal_facts="$(python3 - "$case_dir/preflight_result.json" "$case_dir" <<'PY'
import json, math, sys

def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None

try:
    with open(sys.argv[1], encoding='utf-8') as stream:
        data = json.load(stream)
    reason = data.get('stop_reason')
    allowed = {'completed', 'budget_timeout', 'interrupted', 'floating_point_exception', 'negative_temperature', 'incomplete_checkpoint', 'solver_error'}
    exit_code = data.get('solver_exit_code')
    checkpoint_valid = data.get('checkpoint_valid')
    latest_time = data.get('latest_time')
    latest_value = finite_number(latest_time) if latest_time else None
    requested_end = data.get('requested_end_time_s')
    target_value = finite_number(requested_end) if type(requested_end) in (int, float) else None
    fatal_count = data.get('fatal_count')
    checkpoint_fields = data.get('checkpoint_fields')
    required_fields = {'alpha.polymer', 'T', 'p_rgh', 'U', 'rho'}
    available_fields = set(checkpoint_fields.split(',')) if isinstance(checkpoint_fields, str) else set()
    valid = (
        data.get('schema') == 'clawstack.openfoam.preflight.result.v1'
        and data.get('case_dir') == sys.argv[2]
        and isinstance(reason, str) and reason in allowed
        and type(exit_code) is int and type(checkpoint_valid) is bool
        and isinstance(latest_time, str)
        and (latest_time == '' or (latest_value is not None and latest_value >= 0))
        and target_value is not None and target_value > 0
        and type(fatal_count) is int and fatal_count >= 0
        and (not checkpoint_valid or required_fields.issubset(available_fields))
        and (reason != 'completed' or (exit_code == 0 and checkpoint_valid and fatal_count == 0 and required_fields.issubset(available_fields) and latest_value is not None and latest_value >= target_value - 1e-12))
    )
    if not valid:
        raise ValueError('terminal result failed schema/run/time consistency checks')
    print('\n'.join([reason, str(exit_code), str(checkpoint_valid).lower(), latest_time, str(fatal_count)]))
except Exception:
    sys.exit(2)
PY
        2>/dev/null)" || terminal_facts=''
        [[ -n "$terminal_facts" ]] && break
        sleep 1
    done
    if [[ -z "$terminal_facts" ]]; then
        printf '%s\n' 'KEEPALIVE_STATUS:invalid_terminal_manifest'
        return 4
    fi
    terminal_facts="${terminal_facts//$'\r'/}"
    mapfile -t terminal_fields <<< "$terminal_facts"
    if [[ ${#terminal_fields[@]} -ne 5 ]]; then
        printf '%s\n' 'KEEPALIVE_STATUS:invalid_terminal_manifest'
        return 4
    fi
    stop_reason="${terminal_fields[0]}"
    solver_exit_code="${terminal_fields[1]}"
    checkpoint_valid="${terminal_fields[2]}"
    latest_time="${terminal_fields[3]}"
    fatal_count="${terminal_fields[4]}"
    printf 'KEEPALIVE_SOLVER_EXIT_CODE:%s\n' "$solver_exit_code"
    printf 'KEEPALIVE_CHECKPOINT_VALID:%s\n' "$checkpoint_valid"
    printf 'KEEPALIVE_LATEST_TIME:%s\n' "$latest_time"
    printf 'KEEPALIVE_FATAL_COUNT:%s\n' "$fatal_count"
    if [[ "$stop_reason" == "completed" ]]; then
        printf '%s\n' 'KEEPALIVE_STATUS:solver_completed_target_time'
        printf 'KEEPALIVE_STOP_REASON:%s\n' "$stop_reason"
        return 0
    elif [[ "$stop_reason" =~ ^[a-z_]+$ ]]; then
        printf '%s\n' 'KEEPALIVE_STATUS:terminal_result_written'
        printf 'KEEPALIVE_STOP_REASON:%s\n' "$stop_reason"
        return 0
    fi
    printf '%s\n' 'KEEPALIVE_STATUS:invalid_terminal_manifest'
    return 4
}
if [[ -s "$case_dir/preflight_result.json" ]]; then
    report_terminal_result
    exit $?
fi
launch_deadline=$(( $(date +%s) + 90 ))
seen_active=0
while [[ $(date +%s) -lt $launch_deadline ]]; do
    if systemctl is-active --quiet "$unit"; then
        seen_active=1
        break
    fi
    if [[ -s "$case_dir/preflight_result.json" ]]; then
        report_terminal_result
        exit $?
    fi
    sleep 1
done
if [[ $seen_active -ne 1 ]]; then
    printf '%s\n' 'KEEPALIVE_STATUS:unit_never_active'
    exit 2
fi
while systemctl is-active --quiet "$unit"; do
    [[ -s "$case_dir/preflight_result.json" ]] && break
    sleep 15
done
result_deadline=$(( $(date +%s) + 30 ))
while [[ ! -s "$case_dir/preflight_result.json" && $(date +%s) -lt $result_deadline ]]; do
    sleep 1
done
if [[ -s "$case_dir/preflight_result.json" ]]; then
    report_terminal_result
    exit $?
fi
printf '%s\n' 'KEEPALIVE_STATUS:stopped_without_terminal_result'
exit 3
'@
    return $keepaliveTemplate.Replace('__UNIT__', $Unit).Replace('__CASE_DIR__', $CaseDir).Replace('__READY__', $ReadyPath)
}

function New-CaseArtifactCheckScript([string]$CaseDir) {
    # This launcher is for a fresh case generation, not implicit resume. Keep
    # prior preflight evidence intact and require a new case path for new runs.
    $caseArtifactTemplate = @'
case_dir='__CASE_DIR__'
if [[ ! -d "$case_dir" ]]; then
    printf '%s\n' 'CASE_DIRECTORY_MISSING'
    exit 72
fi
for marker in "$case_dir/preflight_started.json" "$case_dir/preflight_result.json"; do
    if [[ -e "$marker" ]]; then
        printf 'CASE_ALREADY_USED:%s\n' "$marker"
        exit 73
    fi
done
printf '%s\n' 'CASE_ARTIFACTS_CLEAR'
'@
    return $caseArtifactTemplate.Replace('__CASE_DIR__', $CaseDir)
}

if ($WorkerConfigBase64) {
    $worker = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($WorkerConfigBase64)) | ConvertFrom-Json
    if ($worker.schema -ne 'clawstack.openfoam.keepalive_worker.v1' -or
        $worker.unit -notmatch '^[A-Za-z0-9_.@-]+$' -or
        $worker.task_name -notmatch "^ClawstackOpenFoamKeepalive-$([regex]::Escape($worker.unit))-[a-f0-9]{12}$" -or
        $worker.distro -notmatch '^[A-Za-z0-9._ -]+$' -or
        [string]::IsNullOrWhiteSpace($worker.case_dir) -or -not $worker.case_dir.StartsWith('/') -or
        $worker.case_dir -match "['`r`n]" -or
        $worker.ready_path -notmatch '^/tmp/clawstack-openfoam-keepalive-[a-f0-9]{32}\.ready$' -or
        [string]::IsNullOrWhiteSpace($worker.manifest_path) -or
        -not [System.IO.Path]::IsPathRooted($worker.manifest_path)) {
        throw 'Invalid scheduled keepalive worker configuration'
    }
    $ManifestPath = $worker.manifest_path
    $workerExitCode = 1
    $workerOutput = ''
    $monitorStatus = 'monitor_failed'
    $solverStopReason = ''
    $solverExitCode = $null
    $checkpointValid = $null
    $solverLatestTime = $null
    $solverFatalCount = $null
    try {
        $workerScript = New-KeepaliveScript -Unit $worker.unit -CaseDir $worker.case_dir -ReadyPath $worker.ready_path
        $workerScriptBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($workerScript))
        $workerCommand = "echo $workerScriptBase64 | base64 -d | bash"
        $workerArguments = @('-d', $worker.distro, '-u', 'root', '--', 'bash', '-lc', "`"$workerCommand`"")
        $workerOutput = (& wsl.exe @workerArguments 2>&1 | Out-String).Trim()
        $workerExitCode = $LASTEXITCODE
        if ($workerOutput -match '(?m)^KEEPALIVE_STATUS:([a-z_]+)\s*$') {
            $monitorStatus = $Matches[1]
        }
        if ($workerOutput -match '(?m)^KEEPALIVE_STOP_REASON:([a-z_]+)\s*$') {
            $solverStopReason = $Matches[1]
        }
        if ($workerOutput -match '(?m)^KEEPALIVE_SOLVER_EXIT_CODE:(-?\d+)\s*$') { $solverExitCode = [int]$Matches[1] }
        if ($workerOutput -match '(?m)^KEEPALIVE_CHECKPOINT_VALID:(true|false)\s*$') { $checkpointValid = ($Matches[1] -eq 'true') }
        if ($workerOutput -match '(?m)^KEEPALIVE_LATEST_TIME:([0-9.eE+-]*)\s*$') { $solverLatestTime = $Matches[1] }
        if ($workerOutput -match '(?m)^KEEPALIVE_FATAL_COUNT:(\d+)\s*$') { $solverFatalCount = [int]$Matches[1] }
        if (Test-Path -LiteralPath $ManifestPath) {
            Invoke-WithLaunchMutex -Action {
                $launchRecord = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
                if ($launchRecord.schema -ne 'clawstack.openfoam.wsl_detached_launch.v1' -or
                    $launchRecord.keepalive_task_name -ne $worker.task_name -or
                    $launchRecord.unit -ne $worker.unit -or
                    $launchRecord.case_dir -ne $worker.case_dir) {
                    throw 'Refusing to update a host manifest that does not belong to this OpenFOAM run'
                }
                $launchRecord | Add-Member -NotePropertyName keepalive_worker_status -NotePropertyValue $monitorStatus -Force
                $launchRecord | Add-Member -NotePropertyName keepalive_worker_exit_code -NotePropertyValue $workerExitCode -Force
                $launchRecord | Add-Member -NotePropertyName keepalive_worker_finished_utc -NotePropertyValue ((Get-Date).ToUniversalTime().ToString('o')) -Force
                $launchRecord | Add-Member -NotePropertyName keepalive_worker_output -NotePropertyValue $workerOutput.Substring(0, [Math]::Min($workerOutput.Length, 4000)) -Force
                $launchRecord | Add-Member -NotePropertyName solver_stop_reason -NotePropertyValue $solverStopReason -Force
                $launchRecord | Add-Member -NotePropertyName solver_exit_code -NotePropertyValue $solverExitCode -Force
                $launchRecord | Add-Member -NotePropertyName solver_checkpoint_valid -NotePropertyValue $checkpointValid -Force
                $launchRecord | Add-Member -NotePropertyName solver_latest_time -NotePropertyValue $solverLatestTime -Force
                $launchRecord | Add-Member -NotePropertyName solver_fatal_count -NotePropertyValue $solverFatalCount -Force
                if ($launchRecord.status -in @('dispatch_accepted', 'dispatch_outcome_unknown', 'keepalive_ready')) {
                    if ($monitorStatus -eq 'solver_completed_target_time') {
                        $launchRecord.status = 'solver_completed_target_time'
                    }
                    elseif ($monitorStatus -eq 'terminal_result_written') {
                        $launchRecord.status = 'solver_terminal_non_success'
                    }
                    elseif ($monitorStatus -eq 'invalid_terminal_manifest') {
                        $launchRecord.status = 'terminal_manifest_invalid'
                    }
                    elseif ($monitorStatus -eq 'unit_never_active') {
                        $launchRecord.status = 'unit_never_became_active'
                    }
                    elseif ($monitorStatus -eq 'stopped_without_terminal_result') {
                        $launchRecord.status = 'unit_stopped_without_terminal_result'
                    }
                    else {
                        $launchRecord.status = 'keepalive_monitor_failed'
                    }
                }
                Write-LaunchManifest $launchRecord
            }
        }
    }
    finally {
        # Remove only the task whose registered action carries this worker's
        # exact random configuration fingerprint.
        Remove-OwnedKeepaliveTask -TaskName $worker.task_name -ExpectedWorkerConfigBase64 $WorkerConfigBase64 | Out-Null
    }
    exit $workerExitCode
}

# Validate every launcher argument before any WSL call; ValidateOnly exposes
# this gate to operators without creating a task, case, unit, or solver process.
if ($Unit -notmatch '^[A-Za-z0-9_.@-]+$') {
    throw "Invalid systemd unit name: '$Unit'"
}
if ([string]::IsNullOrWhiteSpace($Distro)) {
    throw 'Distro is required'
}
if ([string]::IsNullOrWhiteSpace($CaseDir) -or -not $CaseDir.StartsWith('/')) {
    throw 'CaseDir must be a non-empty absolute Linux path'
}
if ($CaseDir -match "['`r`n]") {
    throw 'CaseDir must not contain single quotes or newlines'
}
if ($BudgetSeconds -lt 1 -or $BudgetSeconds -gt 86400) {
    throw 'BudgetSeconds must be between 1 and 86400'
}
if ($Ranks -lt 1 -or $Ranks -gt 64) {
    throw 'Ranks must be between 1 and 64'
}
$endTimeValue = 0.0
$validEndTime = [double]::TryParse(
    $EndTime,
    [System.Globalization.NumberStyles]::Float,
    [System.Globalization.CultureInfo]::InvariantCulture,
    [ref]$endTimeValue
)
if (-not $validEndTime -or [double]::IsNaN($endTimeValue) -or
    [double]::IsInfinity($endTimeValue) -or $endTimeValue -le 0) {
    throw 'EndTime must be a finite positive number in seconds'
}
if ($LogName -notmatch '^[A-Za-z0-9_.-]+$') {
    throw 'LogName may contain only letters, digits, dot, underscore, and hyphen'
}
if ([string]::IsNullOrWhiteSpace($Runner) -or -not $Runner.StartsWith('/') -or $Runner -match "['`r`n]") {
    throw 'Runner must be a non-empty absolute Linux path without quotes or newlines'
}
if ([string]::IsNullOrWhiteSpace($ManifestPath)) {
    $manifestToken = [guid]::NewGuid().ToString('N')
    $ManifestPath = Join-Path (Get-Location) ("wsl_detached_launch_{0}_{1}.json" -f $Unit, $manifestToken)
}
if (Test-Path -LiteralPath $ManifestPath) {
    throw "ManifestPath already exists; refusing to overwrite a previous run record: $ManifestPath"
}
if ($ValidateOnly) {
    Write-Output 'INPUT_VALIDATION_PASS; no WSL, task, or solver actions performed'
    exit 0
}

function Invoke-WslText([string[]]$Arguments, [int]$TimeoutSeconds = 20) {
    # WSL startup, status probes, or short systemd-run dispatch can stall while
    # a Windows laptop is waking or reconnecting. Bound each call, retain its
    # output and native exit code, and let callers fail closed on timeout.
    $job = Start-Job -ScriptBlock {
        param([string[]]$WslArguments)
        $output = (& wsl.exe @WslArguments 2>&1 | Out-String).Trim()
        [pscustomobject]@{
            Output = $output
            ExitCode = $LASTEXITCODE
        }
    } -ArgumentList (,$Arguments)
    try {
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
        if (-not $completed) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            throw "Timed out after ${TimeoutSeconds}s waiting for read-only WSL status: $($Arguments -join ' ')"
        }
        return Receive-Job -Job $job -ErrorAction Stop | Select-Object -Last 1
    }
    finally {
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
}

$launchMutex = [System.Threading.Mutex]::new($false, 'Global\Clawstack.OpenFOAM.Launch.v1')
$launchMutexAcquired = $false
try {
    $launchMutexAcquired = $launchMutex.WaitOne([TimeSpan]::FromSeconds(10))
}
catch [System.Threading.AbandonedMutexException] {
    # A previous launcher exited unexpectedly; the abandoned mutex is now ours.
    $launchMutexAcquired = $true
}
if (-not $launchMutexAcquired) {
    $launchMutex.Dispose()
    throw 'Another OpenFOAM launcher is in preflight/dispatch; refusing concurrent launch'
}

try {
# Never supersede an older unit implicitly.  The caller must choose a new unit
# and case generation after inspecting an active/failed older generation.
$status = Invoke-WslText @('-d', $Distro, '-u', 'root', '--', 'systemctl', 'is-active', $Unit)
if ($status.ExitCode -notin 0, 3, 4) {
    throw "WSL/systemd preflight failed (exit $($status.ExitCode)): $($status.Output)"
}
$active = $status.Output.Trim()
if ($active -eq 'active' -or $active -eq 'activating') {
    throw "Refusing duplicate launch: systemd unit '$Unit' is already $active"
}
if ($active -ne 'inactive') {
    throw "Refusing launch because systemd state is ambiguous for '$Unit': '$active'"
}

# Check the whole OpenFOAM process family, not only the caller's chosen unit
# name. This prevents a second launcher from overlapping a differently named
# older generation on the same WSL host.
$solverProcessAuditCommand = 'set -o pipefail; ps -eo pid=,ppid=,stat=,comm=,args= | awk ''$4 == "foamRun" || $4 ~ /^mpirun/ {print}'''
$solverProcessAudit = Invoke-WslText @('-d', $Distro, '-u', 'root', '--', 'bash', '-lc', $solverProcessAuditCommand) -TimeoutSeconds 20
if ($solverProcessAudit.ExitCode -ne 0) {
    throw "OpenFOAM process-family audit failed (exit $($solverProcessAudit.ExitCode)): $($solverProcessAudit.Output)"
}
if (-not [string]::IsNullOrWhiteSpace($solverProcessAudit.Output)) {
    throw "Refusing concurrent OpenFOAM solver launch; existing process(es): $($solverProcessAudit.Output)"
}

$caseArtifactCheckScript = New-CaseArtifactCheckScript -CaseDir $CaseDir
$caseArtifactAudit = Invoke-WslText @('-d', $Distro, '-u', 'root', '--', 'bash', '-lc', $caseArtifactCheckScript) -TimeoutSeconds 20
if ($caseArtifactAudit.ExitCode -ne 0 -or $caseArtifactAudit.Output.Trim() -ne 'CASE_ARTIFACTS_CLEAR') {
    throw "Refusing to reuse an old or missing case generation; preserve its evidence and choose a new CaseDir (exit $($caseArtifactAudit.ExitCode)): $($caseArtifactAudit.Output)"
}

$solverArgs = @(
    '-d', $Distro, '-u', 'root', '--', 'systemd-run', '--unit', $Unit,
    '--collect', '--no-block',
    '--setenv=HOME=/root',
    '--setenv=OMPI_ALLOW_RUN_AS_ROOT=1',
    '--setenv=OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1',
    $Runner, $CaseDir, [string]$BudgetSeconds, [string]$Ranks, $EndTime, $LogName, '1'
)

# systemd services do not keep a WSL instance alive, and a child started from a
# remote PowerShell session can be terminated with that session. Let Task
# Scheduler own the WSL monitor so it survives SSH/PowerShell disconnection.
# The task name is unique per launch; an existing exact-name task is never
# overwritten or removed by the parent launcher.
$keepaliveToken = [guid]::NewGuid().ToString('N')
$keepaliveReadyPath = "/tmp/clawstack-openfoam-keepalive-$keepaliveToken.ready"
$keepaliveTaskName = "ClawstackOpenFoamKeepalive-$Unit-$($keepaliveToken.Substring(0,12))"
$keepaliveScript = New-KeepaliveScript -Unit $Unit -CaseDir $CaseDir -ReadyPath $keepaliveReadyPath
$keepaliveEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($keepaliveScript))
$taskConfig = [ordered]@{
    schema = 'clawstack.openfoam.keepalive_worker.v1'
    distro = $Distro
    task_name = $keepaliveTaskName
    unit = $Unit
    case_dir = $CaseDir
    ready_path = $keepaliveReadyPath
    manifest_path = [System.IO.Path]::GetFullPath($ManifestPath)
}
$taskConfigBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($taskConfig | ConvertTo-Json -Compress -Depth 4)))
$existingTask = Get-ScheduledTask -TaskName $keepaliveTaskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($existingTask) {
    throw "Refusing to overwrite pre-existing scheduled task '$keepaliveTaskName'"
}

$record = [ordered]@{
    schema = 'clawstack.openfoam.wsl_detached_launch.v1'
    launched_utc = (Get-Date).ToUniversalTime().ToString('o')
    status = 'keepalive_starting'
    distro = $Distro
    unit = $Unit
    case_dir = $CaseDir
    budget_seconds = $BudgetSeconds
    ranks = $Ranks
    end_time = $EndTime
    runner = $Runner
    solver_dispatch_pid = $null
    solver_dispatch_method = 'synchronous bounded systemd-run --no-block'
    keepalive_task_name = $keepaliveTaskName
    keepalive_ready_path = $keepaliveReadyPath
    keepalive_mode = 'Task Scheduler-owned WSL monitor; readiness-gated; runner stop_reason recorded'
    policy = 'new generation only; no stop/kill/restart of older units or tasks'
}
Write-LaunchManifest $record -CreateOnly

$powerShellExe = Join-Path $PSHOME 'powershell.exe'
$taskAction = New-ScheduledTaskAction -Execute $powerShellExe -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$PSCommandPath`" -WorkerConfigBase64 $taskConfigBase64" -WorkingDirectory (Split-Path -Parent $PSCommandPath)
$taskTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10)
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$taskPrincipal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
try {
    Register-ScheduledTask -TaskName $keepaliveTaskName -TaskPath '\' -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Principal $taskPrincipal -Description 'Temporary WSL keepalive for one OpenFOAM generation; self-removes after monitor exit' | Out-Null
    $record.status = 'keepalive_task_registered'
    Write-LaunchManifest $record
    Start-ScheduledTask -TaskName $keepaliveTaskName -TaskPath '\'
}
catch {
    # This name is unique to this invocation. Remove only our own newly-created
    # task if it is not running; never touch a prior task or any solver unit.
    $taskState = $null
    try { $taskState = (Get-ScheduledTask -TaskName $keepaliveTaskName -TaskPath '\' -ErrorAction Stop).State.ToString() } catch {}
    if ($taskState -eq 'Ready') {
        $removed = Remove-OwnedKeepaliveTask -TaskName $keepaliveTaskName -ExpectedWorkerConfigBase64 $taskConfigBase64
        $record.task_cleanup = if ($removed) { 'removed_owned_task_after_start_failure' } else { 'preserved_task_action_fingerprint_mismatch' }
    }
    $record.status = 'keepalive_task_start_failed_solver_not_dispatched'
    $record.task_state = if ($taskState) { $taskState } else { 'unavailable' }
    $record.task_start_error = $_.Exception.Message
    Write-LaunchManifest $record
    throw
}

# Do not launch the solver until the independent WSL process has created its
# readiness marker. The probe is bounded and read-only; on failure this exits
# before dispatch, leaving the existing cases and units untouched.
$readyProbeCommand = "for i in {1..80}; do test -s '$keepaliveReadyPath' && exit 0; sleep 0.25; done; exit 1"
$readyProbe = Invoke-WslText @('-d', $Distro, '-u', 'root', '--', 'bash', '-lc', $readyProbeCommand) -TimeoutSeconds 25
if ($readyProbe.ExitCode -ne 0) {
    $record.status = 'keepalive_not_ready_solver_not_dispatched'
    $record.keepalive_probe_exit_code = $readyProbe.ExitCode
    $record.keepalive_probe_output = $readyProbe.Output
    try { $record.task_state = (Get-ScheduledTask -TaskName $keepaliveTaskName -TaskPath '\' -ErrorAction Stop).State.ToString() } catch { $record.task_state = 'unavailable' }
    if ($record.task_state -eq 'Ready') {
        $removed = Remove-OwnedKeepaliveTask -TaskName $keepaliveTaskName -ExpectedWorkerConfigBase64 $taskConfigBase64
        $record.task_cleanup = if ($removed) { 'removed_owned_task_after_readiness_failure' } else { 'preserved_task_action_fingerprint_mismatch' }
    }
    Write-LaunchManifest $record
    throw "Keepalive did not become ready; solver was not dispatched (exit $($readyProbe.ExitCode)): $($readyProbe.Output)"
}
$record.status = 'keepalive_ready'
Write-LaunchManifest $record

# systemd-run --no-block returns as soon as systemd accepts the new unit. Use a
# bounded synchronous WSL call so its exit code is audited instead of assuming
# that a detached Windows process successfully submitted the unit.
try {
    $solverDispatch = Invoke-WslText $solverArgs -TimeoutSeconds 30
}
catch {
    # A client timeout does not prove systemd rejected the request. Preserve
    # that ambiguity so the independent monitor can determine whether the unit
    # became active instead of reporting a false dispatch failure.
    $record.status = 'dispatch_outcome_unknown'
    $record.solver_dispatch_error = $_.Exception.Message
    Write-LaunchManifest $record
    throw "systemd-run dispatch outcome is unknown; keepalive will audit the unit: $($record.solver_dispatch_error)"
}
if ($solverDispatch.ExitCode -ne 0) {
    $record.status = 'dispatch_rejected'
    $record.solver_dispatch_exit_code = $solverDispatch.ExitCode
    $record.solver_dispatch_output = $solverDispatch.Output
    Write-LaunchManifest $record
    throw "systemd-run rejected solver dispatch (exit $($solverDispatch.ExitCode)): $($solverDispatch.Output)"
}
$record.status = 'dispatch_accepted'
$record.solver_dispatch_exit_code = $solverDispatch.ExitCode
$record.solver_dispatch_output = $solverDispatch.Output
Write-LaunchManifest $record
Write-Output ("STARTED unit={0} keepalive_task={1} manifest={2}" -f $Unit, $keepaliveTaskName, $ManifestPath)
}
finally {
    if ($launchMutexAcquired) { $launchMutex.ReleaseMutex() }
    $launchMutex.Dispose()
}
