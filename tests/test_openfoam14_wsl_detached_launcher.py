import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "start_openfoam14_wsl_detached.ps1"


def test_launcher_refuses_duplicate_units_and_starts_independent_keepalive():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "Refusing duplicate launch" in text
    assert "'systemctl', 'is-active', $Unit" in text
    assert "Register-ScheduledTask" in text
    assert "Start-ScheduledTask" in text
    assert "Start-Process -FilePath 'wsl.exe'" not in text
    assert "--no-block" in text
    assert "keepalive_task_name" in text


def test_launcher_sets_root_mpi_environment_without_touching_old_units():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "--setenv=HOME=/root" in text
    assert "--setenv=OMPI_ALLOW_RUN_AS_ROOT=1" in text
    assert "--setenv=OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1" in text
    assert "new generation only; no stop/kill/restart of older units" in text


def test_read_only_wsl_preflight_is_bounded_and_fails_closed_on_timeout():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "function Invoke-WslText([string[]]$Arguments, [int]$TimeoutSeconds = 20)" in text
    assert "Wait-Job -Job $job -Timeout $TimeoutSeconds" in text
    assert "Stop-Job -Job $job" in text
    assert "Timed out after ${TimeoutSeconds}s waiting for read-only WSL status" in text


def test_launcher_fails_closed_on_wsl_error_or_non_inactive_unit_state():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "ExitCode = $LASTEXITCODE" in text
    assert "$status.ExitCode -notin 0, 3, 4" in text
    assert "if ($active -ne 'inactive')" in text
    assert "systemd state is ambiguous" in text


def test_keepalive_waits_for_unit_start_and_terminal_manifest():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "launch_deadline=$(( $(date +%s) + 30 ))" in text
    assert "seen_active=1" in text
    assert "preflight_result.json" in text
    assert "keepaliveEncoded" in text
    assert "keepalive_mode" in text
    assert "keepalive_script_base64" not in text
    assert "unit = $Unit" in text
    assert "case_dir = $CaseDir" in text
    assert "ready_path = $keepaliveReadyPath" in text


def test_solver_dispatch_is_gated_on_live_keepalive_readiness():
    text = LAUNCHER.read_text(encoding="utf-8")
    start_keepalive = text.index("Start-ScheduledTask -TaskName $keepaliveTaskName")
    readiness_probe = text.index("$readyProbe = Invoke-WslText")
    solver_dispatch = text.index("$solverDispatch = Invoke-WslText $solverArgs")
    assert start_keepalive < readiness_probe < solver_dispatch
    assert "Keepalive did not become ready; solver was not dispatched" in text
    assert "systemd-run rejected solver dispatch" in text
    assert "solver_dispatch_exit_code = $solverDispatch.ExitCode" in text
    assert "synchronous bounded systemd-run --no-block" in text
    assert "-LogonType Interactive" in text
    assert "Refusing to overwrite pre-existing scheduled task" in text
    assert "function Remove-OwnedKeepaliveTask" in text
    assert "ExpectedWorkerConfigBase64" in text
    assert "task.Actions[0].Arguments.Contains($expectedArgument)" in text
    assert "Remove-OwnedKeepaliveTask -TaskName $worker.task_name" in text
    assert "keepalive_task_start_failed_solver_not_dispatched" in text


def test_cleanup_requires_the_exact_random_task_action_fingerprint():
    text = LAUNCHER.read_text(encoding="utf-8")
    cleanup = text[text.index("function Remove-OwnedKeepaliveTask"):text.index("if ($WorkerConfigBase64)")]
    assert "if (-not $task -or $task.Actions.Count -ne 1) { return $false }" in cleanup
    assert "if (-not $task.Actions[0].Arguments.Contains($expectedArgument)) { return $false }" in cleanup
    assert "Unregister-ScheduledTask" in cleanup


def test_launch_arguments_are_validated_before_any_wsl_probe():
    text = LAUNCHER.read_text(encoding="utf-8")
    first_wsl_probe = text.index("$status = Invoke-WslText")
    checks = [
        "if ([string]::IsNullOrWhiteSpace($Distro))",
        "CaseDir must be a non-empty absolute Linux path",
        "BudgetSeconds must be between 1 and 86400",
        "Ranks must be between 1 and 64",
        "EndTime must be a finite positive number in seconds",
        "LogName may contain only letters, digits, dot, underscore, and hyphen",
        "Runner must be a non-empty absolute Linux path",
    ]
    for check in checks:
        assert text.index(check) < first_wsl_probe
    assert "if ($ValidateOnly)" in text
    assert "no WSL, task, or solver actions performed" in text
    assert text.index("if ($ValidateOnly)") < first_wsl_probe


def test_keepalive_persists_terminal_and_incomplete_run_states():
    text = LAUNCHER.read_text(encoding="utf-8")
    for status in (
        "solver_completed_target_time",
        "terminal_result_written",
        "invalid_terminal_manifest",
        "unit_never_active",
        "stopped_without_terminal_result",
    ):
        assert f"KEEPALIVE_STATUS:{status}" in text
    assert "$monitorStatus = 'monitor_failed'" in text
    assert '"stop_reason"' in text
    assert "KEEPALIVE_STOP_REASON:%s" in text
    assert "$launchRecord.status = 'solver_terminal_non_success'" in text
    assert "manifest_path = [System.IO.Path]::GetFullPath($ManifestPath)" in text
    assert "keepalive_worker_exit_code" in text
    assert "keepalive_worker_finished_utc" in text
    assert "unit_stopped_without_terminal_result" in text
    assert "solver_checkpoint_valid" in text
    assert "solver_latest_time" in text
    assert "solver_fatal_count" in text


def _available_bash():
    if os.name == "nt":
        git_bash = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
        return str(git_bash) if git_bash.is_file() else None
    return shutil.which("bash")


def test_embedded_keepalive_script_parses_and_classifies_runner_results(tmp_path):
    bash = _available_bash()
    if not bash:
        pytest.skip("Bash unavailable; embedded monitor runtime check skipped")

    text = LAUNCHER.read_text(encoding="utf-8")
    template_match = re.search(r"(?ms)^[ \t]*\$keepaliveTemplate = @'\r?\n(.*?)\r?\n[ \t]*'@", text)
    assert template_match
    template = (
        template_match.group(1)
        .replace("__UNIT__", "unit-smoke")
        .replace("__CASE_DIR__", "/tmp/case-smoke")
        .replace("__READY__", "/tmp/ready-smoke")
    )
    parsed = subprocess.run([bash, "-n"], input=template, capture_output=True, text=True, check=False)
    assert parsed.returncode == 0, parsed.stderr

    function_match = re.search(r"(?ms)^report_terminal_result\(\) \{.*?^\}", template)
    assert function_match
    case_dir = str(tmp_path).replace("\\", "/")
    if os.name == "nt":
        case_dir = f"/{case_dir[0].lower()}{case_dir[2:]}"
    for stop_reason, expected_status, checkpoint_valid in (
        ("completed", "solver_completed_target_time", True),
        ("incomplete_checkpoint", "terminal_result_written", False),
        (None, "invalid_terminal_manifest", False),
    ):
        result = (
            {
                "schema": "clawstack.openfoam.preflight.result.v1",
                "stop_reason": stop_reason,
                "solver_exit_code": 0,
                "checkpoint_valid": checkpoint_valid,
                "latest_time": "0.001",
                "fatal_count": 0,
            }
            if stop_reason
            else {"schema": "invalid"}
        )
        (tmp_path / "preflight_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        script = f"case_dir='{case_dir}'\n{function_match.group(0)}\nreport_terminal_result"
        if os.name == "nt":
            script = 'python3() { python "$@"; }\n' + script
        outcome = subprocess.run([bash, "-c", script], capture_output=True, text=True, check=False)
        assert expected_status in outcome.stdout
        assert (outcome.returncode == 0) is (stop_reason is not None)


def test_task_cleanup_runtime_mock_preserves_fingerprint_mismatch():
    powershell = shutil.which("powershell.exe") if os.name == "nt" else shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell unavailable; scheduled-task mock check skipped")

    text = LAUNCHER.read_text(encoding="utf-8")
    helper_match = re.search(
        r"(?ms)^function Remove-OwnedKeepaliveTask\([^\n]*\) \{.*?^\}", text
    )
    assert helper_match
    script = f"""
$script:Unregistered = 0
$script:TaskActions = @([pscustomobject]@{{ Arguments = '-WorkerConfigBase64 AbC123+/=' }})
function Get-ScheduledTask {{ param($TaskName, $TaskPath, $ErrorAction); [pscustomobject]@{{ Actions = $script:TaskActions }} }}
function Unregister-ScheduledTask {{ param($TaskName, $TaskPath, $Confirm, $ErrorAction); $script:Unregistered++ }}
{helper_match.group(0)}
$exact = Remove-OwnedKeepaliveTask -TaskName 'ClawstackOpenFoamKeepalive-unit-aaaaaaaaaaaa' -ExpectedWorkerConfigBase64 'AbC123+/='
if (-not $exact -or $script:Unregistered -ne 1) {{ exit 11 }}
$script:TaskActions = @([pscustomobject]@{{ Arguments = '-WorkerConfigBase64 different-token' }})
$mismatch = Remove-OwnedKeepaliveTask -TaskName 'ClawstackOpenFoamKeepalive-unit-aaaaaaaaaaaa' -ExpectedWorkerConfigBase64 'AbC123+/='
if ($mismatch -or $script:Unregistered -ne 1) {{ exit 12 }}
$script:TaskActions = @(
    [pscustomobject]@{{ Arguments = '-WorkerConfigBase64 AbC123+/=' }},
    [pscustomobject]@{{ Arguments = '-OtherAction' }}
)
$multiple = Remove-OwnedKeepaliveTask -TaskName 'ClawstackOpenFoamKeepalive-unit-aaaaaaaaaaaa' -ExpectedWorkerConfigBase64 'AbC123+/='
if ($multiple -or $script:Unregistered -ne 1) {{ exit 13 }}
Write-Output 'SCHEDULED_TASK_CLEANUP_MOCK_PASS'
"""
    result = subprocess.run([powershell, "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "SCHEDULED_TASK_CLEANUP_MOCK_PASS" in result.stdout


def test_existing_openfoam_process_family_blocks_any_new_unit_generation():
    text = LAUNCHER.read_text(encoding="utf-8")
    audit = text.index("$solverProcessAudit = Invoke-WslText")
    registration = text.index("Register-ScheduledTask -TaskName $keepaliveTaskName")
    dispatch = text.index("$solverDispatch = Invoke-WslText $solverArgs")
    assert "ps -eo pid=,ppid=,stat=,comm=,args=" in text
    assert '$4 == "foamRun" || $4 ~ /^mpirun/' in text
    assert "Refusing concurrent OpenFOAM solver launch" in text
    assert audit < registration < dispatch


def test_process_family_awk_gate_detects_solver_but_ignores_idle_host():
    bash = _available_bash()
    if not bash:
        pytest.skip("Bash unavailable; process-family runtime check skipped")
    text = LAUNCHER.read_text(encoding="utf-8")
    command_match = re.search(r"(?m)^\$solverProcessAuditCommand = '(.*?)'$", text)
    assert command_match
    command = command_match.group(1).replace("''", "'")

    def audit(line):
        script = f"ps() {{ printf '%s\\n' {shlex.quote(line)}; }}\n{command}"
        return subprocess.run([bash, "-c", script], capture_output=True, text=True, check=False)

    assert audit("").stdout.strip() == ""
    assert "foamRun" in audit("111 1 R foamRun foamRun -solver compressibleVoF").stdout
    assert "mpirun" in audit("222 1 Sl mpirun.openmpi mpirun -np 2 foamRun").stdout


def test_launcher_serializes_preflight_and_dispatch_with_host_mutex():
    text = LAUNCHER.read_text(encoding="utf-8")
    lock = text.index("$launchMutex = [System.Threading.Mutex]::new")
    wsl_probe = text.index("$status = Invoke-WslText")
    task_registration = text.index("Register-ScheduledTask -TaskName $keepaliveTaskName")
    solver_dispatch = text.index("$solverDispatch = Invoke-WslText $solverArgs")
    release = text.index("$launchMutex.ReleaseMutex()")
    assert lock < wsl_probe < task_registration < solver_dispatch < release
    assert "Another OpenFOAM launcher is in preflight/dispatch" in text


def test_global_mutex_excludes_a_second_powershell_process(tmp_path):
    powershell = shutil.which("powershell.exe") if os.name == "nt" else shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell unavailable; cross-process mutex test skipped")
    name = f"Global\\ClawstackOpenFoamTest-{uuid.uuid4().hex}"
    marker = str(tmp_path / "mutex-ready.txt").replace("'", "''")
    first_script = f"""
$m = [System.Threading.Mutex]::new($false, '{name}')
if (-not $m.WaitOne(0)) {{ exit 11 }}
[IO.File]::WriteAllText('{marker}', 'locked')
Start-Sleep -Seconds 3
$m.ReleaseMutex(); $m.Dispose()
"""
    second_script = f"""
$m = [System.Threading.Mutex]::new($false, '{name}')
$acquired = $m.WaitOne(0)
if ($acquired) {{ $m.ReleaseMutex(); $m.Dispose(); exit 12 }}
$m.Dispose(); Write-Output 'LOCK_CONTENDED'
"""
    first = subprocess.Popen([powershell, "-NoProfile", "-Command", first_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline and not Path(marker).exists():
            time.sleep(0.05)
        assert Path(marker).exists(), "first process did not acquire the named mutex"
        second = subprocess.run([powershell, "-NoProfile", "-Command", second_script], capture_output=True, text=True, check=False)
        assert second.returncode == 0, second.stderr
        assert "LOCK_CONTENDED" in second.stdout
        _, first_error = first.communicate(timeout=5)
        assert first.returncode == 0, first_error
    finally:
        if first.poll() is None:
            first.terminate()
            first.communicate(timeout=5)


def test_manifest_writer_atomically_creates_and_replaces_json(tmp_path):
    powershell = shutil.which("powershell.exe") if os.name == "nt" else shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell unavailable; manifest writer integration skipped")
    text = LAUNCHER.read_text(encoding="utf-8")
    helper = re.search(r"(?ms)^function Write-LaunchManifest\([^\n]*\) \{.*?^\}", text)
    assert helper
    manifest = str(tmp_path / "atomic-launch.json").replace("'", "''")
    script = f"""
$global:ManifestPath = '{manifest}'
{helper.group(0)}
$first = [ordered]@{{ schema = 'test.v1'; status = 'initial' }}
Write-LaunchManifest $first
$afterFirst = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($afterFirst.status -ne 'initial') {{ exit 11 }}
$first.status = 'updated'
Write-LaunchManifest $first
$afterSecond = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($afterSecond.status -ne 'updated') {{ exit 12 }}
$writeBlocked = $false
$lock = [System.IO.File]::Open($ManifestPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
try {{
    $first.status = 'must-not-replace'
    try {{ Write-LaunchManifest $first }} catch {{ $writeBlocked = $true }}
}}
finally {{ $lock.Dispose() }}
if (-not $writeBlocked) {{ exit 14 }}
$afterBlocked = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($afterBlocked.status -ne 'updated') {{ exit 15 }}
$leftovers = @(Get-ChildItem -LiteralPath (Split-Path -Parent $ManifestPath) -Filter 'atomic-launch.json.*.tmp') + @(Get-ChildItem -LiteralPath (Split-Path -Parent $ManifestPath) -Filter 'atomic-launch.json.*.bak')
if ($leftovers.Count -ne 0) {{ exit 16 }}
Write-Output 'ATOMIC_MANIFEST_CREATE_REPLACE_FAILURE_PRESERVES_OLD_PASS'
"""
    result = subprocess.run([powershell, "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "ATOMIC_MANIFEST_CREATE_REPLACE_FAILURE_PRESERVES_OLD_PASS" in result.stdout


def test_worker_finalizes_host_manifest_without_real_wsl_or_scheduled_task(tmp_path):
    powershell = shutil.which("powershell.exe") if os.name == "nt" else shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell unavailable; worker mock integration skipped")

    manifest = tmp_path / "launch.json"
    cleanup_marker = tmp_path / "task-cleanup.marker"
    worker = {
        "schema": "clawstack.openfoam.keepalive_worker.v1",
        "distro": "Ubuntu-22.04",
        "task_name": "ClawstackOpenFoamKeepalive-test-unit-012345abcdef",
        "unit": "test-unit",
        "case_dir": "/home/test/case",
        "ready_path": "/tmp/clawstack-openfoam-keepalive-0123456789abcdef0123456789abcdef.ready",
        "manifest_path": str(manifest.resolve()),
    }
    manifest.write_text(json.dumps({
        "schema": "clawstack.openfoam.wsl_detached_launch.v1",
        "status": "dispatch_accepted",
        "keepalive_task_name": worker["task_name"],
        "unit": worker["unit"],
        "case_dir": worker["case_dir"],
    }), encoding="utf-8")
    worker_config = base64.b64encode(json.dumps(worker).encode("utf-8")).decode("ascii")
    action_args = f"-WorkerConfigBase64 {worker_config}"
    launcher = str(LAUNCHER).replace("'", "''")
    marker = str(cleanup_marker).replace("'", "''")
    script = f"""
$global:TaskActionArguments = '{action_args}'
function Get-ScheduledTask {{ param($TaskName, $TaskPath, $ErrorAction); [pscustomobject]@{{ Actions = @([pscustomobject]@{{ Arguments = $global:TaskActionArguments }}) }} }}
function Unregister-ScheduledTask {{ param($TaskName, $TaskPath, $Confirm, $ErrorAction); [IO.File]::WriteAllText('{marker}', 'removed') }}
function Mock-Wsl {{ Write-Output 'KEEPALIVE_STATUS:solver_completed_target_time'; Write-Output 'KEEPALIVE_STOP_REASON:completed'; Write-Output 'KEEPALIVE_SOLVER_EXIT_CODE:0'; Write-Output 'KEEPALIVE_CHECKPOINT_VALID:true'; Write-Output 'KEEPALIVE_LATEST_TIME:0.001'; Write-Output 'KEEPALIVE_FATAL_COUNT:0'; $global:LASTEXITCODE = 0 }}
Set-Alias -Name 'wsl.exe' -Value Mock-Wsl
& '{launcher}' -WorkerConfigBase64 '{worker_config}'
"""
    run = subprocess.run([powershell, "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    assert run.returncode == 0, run.stderr
    assert cleanup_marker.read_text(encoding="utf-8") == "removed"
    updated = json.loads(manifest.read_text(encoding="utf-8-sig"))
    assert updated["status"] == "solver_completed_target_time"
    assert updated["solver_stop_reason"] == "completed"
    assert updated["solver_exit_code"] == 0
    assert updated["solver_checkpoint_valid"] is True
    assert updated["solver_latest_time"] == "0.001"
    assert updated["solver_fatal_count"] == 0
    assert updated["keepalive_worker_status"] == "solver_completed_target_time"
    assert updated["keepalive_worker_exit_code"] == 0

    unrelated = {"schema": "other.application.v1", "status": "must-remain-unchanged"}
    manifest.write_text(json.dumps(unrelated), encoding="utf-8")
    rejected = subprocess.run([powershell, "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    assert rejected.returncode != 0
    assert "does not belong to this OpenFOAM run" in rejected.stderr
    assert json.loads(manifest.read_text(encoding="utf-8-sig")) == unrelated
