from pathlib import Path


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
