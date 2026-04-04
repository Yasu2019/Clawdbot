#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from docker_runtime import docker_command, docker_compose_command


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "repair_learning_engine_status.json"
STATE_PATH = WORKSPACE / "repair_learning_engine_state.json"
RESTART_DOCKER_SCRIPT = WORKSPACE / "restart_docker.ps1"
DOCKER_RUNTIME_CONFIG = WORKSPACE / "docker_runtime_config.json"
BASE_COMPOSE = ROOT / "clawstack_v2" / "docker-compose.yml"
PATCH_COMPOSE = ROOT / "clawstack_v2" / "docker-compose.learning_engine.patch.yml"
HEALTH_URLS = [
    "http://localhost:8110/health",
    "http://127.0.0.1:8110/health",
    "http://host.docker.internal:8110/health",
]


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def run_command(command: list[str], timeout_seconds: int) -> dict[str, Any]:
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


def docker_api_check() -> dict[str, Any]:
    result = run_command(docker_command("version"), 60)
    ok = result.get("returncode") == 0 and "Server:" in result.get("stdout", "")
    return {
        "ok": ok,
        "result": result,
    }


def learning_health() -> dict[str, Any]:
    attempts = []
    for url in HEALTH_URLS:
        try:
            resp = requests.get(url, timeout=10)
            attempts.append({"url": url, "status": resp.status_code})
            if resp.ok:
                return {
                    "ok": True,
                    "url": url,
                    "status": resp.status_code,
                    "payload": resp.json(),
                    "attempts": attempts,
                }
        except Exception as exc:
            attempts.append({"url": url, "error": str(exc)})
    return {"ok": False, "attempts": attempts}


def can_restart_docker(state: dict[str, Any], cooldown_minutes: int) -> bool:
    last = parse_dt((state.get("dockerRestart") or {}).get("lastAt"))
    if last is None:
        return True
    return (now_jst().astimezone(last.tzinfo) - last) >= timedelta(minutes=cooldown_minutes)


def docker_runtime_mode() -> str:
    config = read_json(DOCKER_RUNTIME_CONFIG)
    mode = str(config.get("mode") or "").strip()
    return mode or "legacy"


def mark_restart(state: dict[str, Any]) -> None:
    state["dockerRestart"] = {"lastAt": now_jst_text()}
    write_json(STATE_PATH, state)


def wait_for_learning_engine(total_seconds: int, poll_seconds: int) -> dict[str, Any]:
    deadline = time.time() + total_seconds
    attempts = []
    while time.time() < deadline:
        health = learning_health()
        attempts.append(health)
        if health.get("ok"):
            return {"ok": True, "attempts": attempts, "health": health}
        time.sleep(poll_seconds)
    return {"ok": False, "attempts": attempts}


def main() -> int:
    state = read_json(STATE_PATH)
    runtime_mode = docker_runtime_mode()
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "stage": "starting",
        "dockerRuntimeMode": runtime_mode,
        "dockerApi": {},
        "learningHealthBefore": {},
        "actions": [],
    }
    write_json(STATUS_PATH, status)

    before = learning_health()
    status["learningHealthBefore"] = before
    if before.get("ok"):
        status["stage"] = "completed"
        status["finishedAt"] = now_jst_text()
        status["result"] = "already_healthy"
        write_json(STATUS_PATH, status)
        return 0

    docker_status = docker_api_check()
    status["dockerApi"] = docker_status
    write_json(STATUS_PATH, status)

    if not docker_status.get("ok"):
        status["stage"] = "restart_docker_desktop"
        if runtime_mode == "wsl_native":
            status["actions"].append(
                {
                    "key": "restart_docker_desktop",
                    "result": {
                        "skipped": True,
                        "reason": "headless native docker mode active; refusing Docker Desktop / WSL restart",
                    },
                }
            )
        elif can_restart_docker(state, cooldown_minutes=120):
            restart_result = run_command(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(RESTART_DOCKER_SCRIPT),
                ],
                240,
            )
            status["actions"].append({"key": "restart_docker_desktop", "result": restart_result})
            if restart_result.get("returncode") == 0:
                mark_restart(state)
            time.sleep(45)
        else:
            status["actions"].append(
                {
                    "key": "restart_docker_desktop",
                    "result": {"skipped": True, "reason": "docker restart cooldown active"},
                }
            )
        status["dockerApiAfterRestart"] = docker_api_check()
        write_json(STATUS_PATH, status)

    if runtime_mode == "wsl_native":
        status["stage"] = "completed"
        status["finishedAt"] = now_jst_text()
        status["result"] = "skipped_in_headless_native_mode"
        status["actions"].append(
            {
                "key": "compose_up_learning_engine",
                "result": {
                    "skipped": True,
                    "reason": "headless native docker mode active; learning_engine compose repair disabled until native compose path is corrected",
                },
            }
        )
        write_json(STATUS_PATH, status)
        return 0

    status["stage"] = "compose_up_learning_engine"
    compose_result = run_command(
        docker_compose_command(
            "-f",
            str(BASE_COMPOSE),
            "-f",
            str(PATCH_COMPOSE),
            "up",
            "-d",
            "learning_engine",
        ),
        300,
    )
    status["actions"].append({"key": "compose_up_learning_engine", "result": compose_result})
    write_json(STATUS_PATH, status)

    status["stage"] = "wait_for_health"
    wait_result = wait_for_learning_engine(total_seconds=180, poll_seconds=10)
    status["learningHealthAfter"] = wait_result
    status["finishedAt"] = now_jst_text()
    status["stage"] = "completed"
    status["result"] = "recovered" if wait_result.get("ok") else "still_offline"
    write_json(STATUS_PATH, status)
    return 0 if wait_result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
