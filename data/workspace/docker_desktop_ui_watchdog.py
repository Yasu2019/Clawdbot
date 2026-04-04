#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).absolute().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "docker_desktop_ui_watchdog_status.json"
STATE_PATH = WORKSPACE / "docker_desktop_ui_watchdog_state.json"
CONFIG_PATH = WORKSPACE / "docker_desktop_ui_watchdog_config.json"
HARNESS_PATH = ROOT / "data" / "state" / "docker_desktop_ui_watchdog" / "harness_status.json"
RESET_SCRIPT = ROOT / "scripts" / "reset_docker_desktop_frontend_cache.ps1"
STOP_FRONTEND_SCRIPT = ROOT / "scripts" / "stop_docker_desktop_frontend_only.ps1"
DOCKER_CLI = Path(r"C:\Program Files\Docker\Docker\resources\bin\docker.exe")
FRONTEND_EXE = Path(r"C:\Program Files\Docker\Docker\frontend\Docker Desktop.exe")
PROFILE_ROOT = Path.home() / "AppData" / "Roaming" / "Docker Desktop"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_command(command: list[str], timeout_seconds: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def get_main_frontend_processes() -> list[dict[str, Any]]:
    ps_script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'Docker Desktop.exe' -and $_.CommandLine -like '*--reason=open-tray*' } | "
        "Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Depth 4"
    )
    result = run_command(["powershell", "-NoProfile", "-Command", ps_script], 20)
    if result.get("returncode") not in (0, None) or not result.get("stdout"):
        return []
    try:
        payload = json.loads(result["stdout"])
    except Exception:
        return []
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return payload
    return []


def docker_probe() -> dict[str, Any]:
    version = run_command([str(DOCKER_CLI), "version", "--format", "{{json .Server}}"], 90)
    stats = run_command(
        [str(DOCKER_CLI), "stats", "--all", "--no-trunc", "--no-stream", "--format", "{{json .}}"],
        90,
    )
    return {
        "version": version,
        "stats": stats,
        "ok": version.get("returncode") == 0 and stats.get("returncode") == 0,
    }


def docker_version_probe() -> dict[str, Any]:
    version = run_command([str(DOCKER_CLI), "version", "--format", "{{json .Server}}"], 90)
    return {
        "version": version,
        "stats": {},
        "ok": version.get("returncode") == 0,
    }


def should_reset(state: dict[str, Any], cooldown_minutes: int) -> bool:
    last_reset = parse_dt(str((state.get("lastReset") or {}).get("at") or ""))
    if last_reset is None:
        return True
    return (now_jst().astimezone(last_reset.tzinfo) - last_reset) >= timedelta(minutes=cooldown_minutes)


def run_reset() -> dict[str, Any]:
    return run_command(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(RESET_SCRIPT)],
        300,
    )


def run_stop_frontend_only() -> dict[str, Any]:
    return run_command(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(STOP_FRONTEND_SCRIPT)],
        180,
    )


def write_harness(status: dict[str, Any]) -> None:
    payload = {
        "updatedAt": status.get("updatedAt"),
        "service": "docker_desktop_ui_watchdog",
        "state": status.get("stage"),
        "reason": status.get("reason"),
        "lastAction": status.get("lastAction"),
        "frontendCount": status.get("frontendCount"),
        "dockerOk": status.get("dockerOk"),
    }
    save_json(HARNESS_PATH, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchdog for Docker Desktop UI instability")
    parser.add_argument("--poll-seconds", type=int, default=3)
    parser.add_argument("--reset-cooldown-minutes", type=int, default=180)
    parser.add_argument("--quiet-recheck-seconds", type=int, default=3)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = load_json(STATE_PATH, {})
    config = load_json(CONFIG_PATH, {})
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "pid": os.getpid(),
        "stage": "starting",
        "reason": "",
        "lastAction": "",
    }

    while True:
        config = load_json(CONFIG_PATH, config)
        quiet_mode = bool(config.get("quietMode", False))
        allow_ui_reset = bool(config.get("allowUiReset", False))
        failure_threshold = max(1, int(config.get("consecutiveFailuresForReset", 6)))
        status["updatedAt"] = now_jst_text()
        status["quietMode"] = quiet_mode
        status["allowUiReset"] = allow_ui_reset
        status["consecutiveFailuresForReset"] = failure_threshold
        status["frontendExeExists"] = FRONTEND_EXE.exists()
        status["dockerCliExists"] = DOCKER_CLI.exists()
        status["profileRootExists"] = PROFILE_ROOT.exists()
        frontends = get_main_frontend_processes()
        status["lastAction"] = ""

        if quiet_mode and frontends:
            stop_result = run_stop_frontend_only()
            status["lastAction"] = "stop_frontend_for_quiet_mode"
            status["stopFrontendResult"] = stop_result
            time.sleep(max(1, args.quiet_recheck_seconds))
            frontends = get_main_frontend_processes()
            status["quietResidualFrontendCount"] = len(frontends)
            status["quietResidualFrontendProcesses"] = frontends
            state["lastQuietStop"] = {
                "at": now_jst_text(),
                "result": stop_result,
            }
            save_json(STATE_PATH, state)

        status["frontendCount"] = len(frontends)
        status["frontendProcesses"] = frontends

        if status["dockerCliExists"]:
            probe = docker_version_probe() if quiet_mode else docker_probe()
        else:
            probe = {"ok": False, "version": {}, "stats": {}}
        status["dockerProbe"] = probe
        status["dockerOk"] = bool(probe.get("ok"))

        unhealthy = False
        reason = "healthy"
        if not status["dockerCliExists"]:
            unhealthy = True
            reason = "docker cli missing"
        elif not status["frontendExeExists"]:
            unhealthy = True
            reason = "docker desktop frontend missing"
        elif status["frontendCount"] == 0 and not quiet_mode:
            unhealthy = True
            reason = "docker desktop dashboard is not running"
        elif not status["dockerOk"]:
            unhealthy = True
            version_stderr = probe.get("version", {}).get("stderr") or probe.get("version", {}).get("stdout") or ""
            stats_stderr = probe.get("stats", {}).get("stderr") or probe.get("stats", {}).get("stdout") or ""
            reason = f"docker probe failed: version={version_stderr[:160]} stats={stats_stderr[:160]}"
        elif quiet_mode and status["frontendCount"] == 0:
            reason = "quiet mode active; frontend intentionally stopped"
        elif quiet_mode and status["frontendCount"] > 0:
            reason = "quiet mode active; dashboard is being suppressed but respawns quickly"

        status["reason"] = reason
        status["stage"] = "suppressing" if quiet_mode and status["frontendCount"] > 0 else ("repairing" if unhealthy else "healthy")

        previous_failures = int(state.get("consecutiveFailures", 0) or 0)
        current_failures = previous_failures + 1 if unhealthy else 0
        state["consecutiveFailures"] = current_failures
        status["consecutiveFailures"] = current_failures

        if unhealthy and not allow_ui_reset:
            status["lastAction"] = "observe_only_no_ui_reset"
        elif unhealthy and current_failures < failure_threshold:
            status["lastAction"] = "observe_only_threshold_not_met"
        elif unhealthy and should_reset(state, args.reset_cooldown_minutes):
            reset_result = run_reset()
            state["lastReset"] = {
                "at": now_jst_text(),
                "reason": reason,
                "result": reset_result,
            }
            status["lastAction"] = "reset_frontend_cache"
            status["resetResult"] = reset_result
            save_json(STATE_PATH, state)
        elif unhealthy:
            status["lastAction"] = "cooldown_skip"
            status["cooldownUntil"] = (
                parse_dt(str((state.get("lastReset") or {}).get("at") or "")) + timedelta(minutes=args.reset_cooldown_minutes)
            ).strftime("%Y-%m-%d %H:%M:%S JST") if parse_dt(str((state.get("lastReset") or {}).get("at") or "")) else None

        save_json(STATUS_PATH, status)
        write_harness(status)

        if args.once:
            return
        time.sleep(max(1, args.poll_seconds))


if __name__ == "__main__":
    main()
