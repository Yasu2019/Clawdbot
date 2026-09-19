import json
import os
import re
import shlex
import shutil
import subprocess
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
    template_match = re.search(r"(?ms)^\$keepaliveTemplate = @'\r?\n(.*?)\r?\n'@", text)
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
    for stop_reason, expected_status in (
        ("completed", "solver_completed_target_time"),
        ("incomplete_checkpoint", "terminal_result_written"),
        (None, "invalid_terminal_manifest"),
    ):
        result = (
            {"schema": "clawstack.openfoam.preflight.result.v1", "stop_reason": stop_reason}
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
