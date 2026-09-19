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
    [string]$ManifestPath = (Join-Path (Get-Location) 'wsl_detached_launch.json'),
    [string]$WorkerConfigBase64 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-LaunchManifest([System.Collections.IDictionary]$Record) {
    $parent = Split-Path -Parent $ManifestPath
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    $Record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
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

if ($WorkerConfigBase64) {
    $worker = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($WorkerConfigBase64)) | ConvertFrom-Json
    if ($worker.schema -ne 'clawstack.openfoam.keepalive_worker.v1' -or
        $worker.keepalive_script_base64 -notmatch '^[A-Za-z0-9+/=]+$' -or
        $worker.task_name -notmatch '^ClawstackOpenFoamKeepalive-[A-Za-z0-9_.@-]+-[a-f0-9]{12}$') {
        throw 'Invalid scheduled keepalive worker configuration'
    }
    $workerExitCode = 1
    try {
        $workerCommand = "echo $($worker.keepalive_script_base64) | base64 -d | bash"
        $workerArguments = @('-d', $worker.distro, '-u', 'root', '--', 'bash', '-lc', "`"$workerCommand`"")
        & wsl.exe @workerArguments
        $workerExitCode = $LASTEXITCODE
    }
    finally {
        # Remove only the task whose registered action carries this worker's
        # exact random configuration fingerprint.
        Remove-OwnedKeepaliveTask -TaskName $worker.task_name -ExpectedWorkerConfigBase64 $WorkerConfigBase64 | Out-Null
    }
    exit $workerExitCode
}

if ($Unit -notmatch '^[A-Za-z0-9_.@-]+$') {
    throw "Invalid systemd unit name: '$Unit'"
}
if ($CaseDir -match "['`r`n]") {
    throw 'CaseDir must not contain single quotes or newlines'
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
$keepaliveTemplate = @'
unit='__UNIT__'
case_dir='__CASE_DIR__'
ready='__READY__'
trap 'rm -f -- "$ready"' EXIT
printf '%s\n' "$$" > "$ready"
launch_deadline=$(( $(date +%s) + 30 ))
seen_active=0
while [[ $(date +%s) -lt $launch_deadline ]]; do
    if systemctl is-active --quiet "$unit"; then
        seen_active=1
        break
    fi
    if [[ -s "$case_dir/preflight_result.json" ]]; then
        exit 0
    fi
    sleep 1
done
if [[ $seen_active -ne 1 ]]; then
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
'@
$keepaliveScript = $keepaliveTemplate.Replace('__UNIT__', $Unit).Replace('__CASE_DIR__', $CaseDir).Replace('__READY__', $keepaliveReadyPath)
$keepaliveEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($keepaliveScript))
$taskConfig = [ordered]@{
    schema = 'clawstack.openfoam.keepalive_worker.v1'
    distro = $Distro
    task_name = $keepaliveTaskName
    keepalive_script_base64 = $keepaliveEncoded
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
    keepalive_mode = 'Task Scheduler-owned WSL monitor; readiness-gated; bounded launch/finalize grace'
    policy = 'new generation only; no stop/kill/restart of older units or tasks'
}
Write-LaunchManifest $record

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
$solverDispatch = Invoke-WslText $solverArgs -TimeoutSeconds 30
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
