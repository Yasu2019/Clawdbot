#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "email_continuous_watchdog_status.json"
STATE_PATH = WORKSPACE / "email_continuous_watchdog_state.json"
HARNESS_PATH = ROOT / "data" / "state" / "email_continuous_ingest" / "harness_status.json"
NODE_GMAIL_SCRIPT = WORKSPACE / "scripts" / "send_allowed_gmail_from_b64.js"
TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"
GMAIL_RECIPIENT = "y.suzuki.hk@gmail.com"
DAEMON_TOKEN = "continuous_email_ingest_daemon.py"


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


def encode_b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def send_telegram(text: str) -> dict[str, Any]:
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_gmail(subject: str, body: str) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "node",
            str(NODE_GMAIL_SCRIPT),
            GMAIL_RECIPIENT,
            encode_b64url(subject),
            encode_b64url(body),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


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


def list_daemon_processes() -> list[dict[str, Any]]:
    ps_script = (
        "Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{DAEMON_TOKEN}*' }} | "
        "Select-Object ProcessId, Name, CommandLine | ConvertTo-Json -Compress"
    )
    result = run_command(["powershell", "-NoProfile", "-Command", ps_script], timeout_seconds=30)
    stdout = result.get("stdout", "")
    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except Exception:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def stop_daemon_processes(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for item in processes:
        pid = item.get("ProcessId")
        if not pid:
            continue
        results.append(run_command(["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"], 30))
    return results


def start_daemon() -> dict[str, Any]:
    daemon_path = str(WORKSPACE / "continuous_email_ingest_daemon.py")
    try:
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(
            [
                "python3",
                daemon_path,
                "--poll-seconds",
                "300",
                "--learning-interval-cycles",
                "3",
                "--full-backfill-interval-cycles",
                "72",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creationflags,
        )
        return {
            "command": f"python3 {daemon_path} --poll-seconds 300 --learning-interval-cycles 3 --full-backfill-interval-cycles 72",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "timedOut": False,
            "startedPid": proc.pid,
        }
    except Exception as exc:
        return {
            "command": f"python3 {daemon_path} --poll-seconds 300 --learning-interval-cycles 3 --full-backfill-interval-cycles 72",
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "timedOut": False,
        }


def daemon_health(stale_minutes: int) -> tuple[bool, str, dict[str, Any], list[dict[str, Any]]]:
    harness = load_json(HARNESS_PATH, {})
    processes = list_daemon_processes()
    updated_at = parse_dt(harness.get("updatedAt") or harness.get("lastSuccessAt"))
    stage = str(harness.get("state") or "")
    if not processes:
        return False, "daemon process missing", harness, processes
    if updated_at is None:
        return False, "daemon heartbeat missing", harness, processes
    if (now_jst().astimezone(updated_at.tzinfo) - updated_at) >= timedelta(minutes=stale_minutes):
        return False, "daemon heartbeat stale", harness, processes
    if stage == "error":
        return False, "daemon reported error state", harness, processes
    return True, "healthy", harness, processes


def should_notify(state: dict[str, Any], key: str, cooldown_minutes: int) -> bool:
    sent = (state.get("notifications") or {}).get(key, {})
    sent_at = parse_dt(sent.get("sentAt"))
    if sent_at is None:
        return True
    return (now_jst().astimezone(sent_at.tzinfo) - sent_at) >= timedelta(minutes=cooldown_minutes)


def remember_notification(state: dict[str, Any], key: str, detail: str) -> None:
    state.setdefault("notifications", {})
    state["notifications"][key] = {"sentAt": now_jst_text(), "detail": detail}


def write_status(status: dict[str, Any]) -> None:
    save_json(STATUS_PATH, status)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchdog for continuous email ingest daemon")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--stale-minutes", type=int, default=15)
    parser.add_argument("--notify-cooldown-minutes", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    state = load_json(STATE_PATH, {})
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "updatedAt": now_jst_text(),
        "stage": "running",
        "pid": os.getpid(),
        "lastReason": "",
        "lastAction": "",
        "lastHarness": {},
        "lastProcessCount": 0,
    }

    while True:
        healthy, reason, harness, processes = daemon_health(args.stale_minutes)
        status["updatedAt"] = now_jst_text()
        status["lastReason"] = reason
        status["lastHarness"] = harness
        status["lastProcessCount"] = len(processes)

        if healthy:
            status["lastAction"] = "none"
            write_status(status)
            save_json(STATE_PATH, state)
            if args.once:
                break
            time.sleep(max(args.poll_seconds, 30))
            continue

        stop_results = stop_daemon_processes(processes)
        start_result = start_daemon()
        status["lastAction"] = "restart_daemon"
        status["restart"] = {
            "reason": reason,
            "stopResults": stop_results,
            "startResult": start_result,
        }
        write_status(status)

        notify_key = f"restart:{reason}"
        if should_notify(state, notify_key, args.notify_cooldown_minutes):
            body = (
                "Email continuous ingest watchdog restarted the daemon.\n"
                f"Time: {now_jst_text()}\n"
                f"Reason: {reason}\n"
                f"Known stage: {harness.get('state')}\n"
                f"Known updatedAt: {harness.get('updatedAt')}\n"
                f"Process count before restart: {len(processes)}"
            )
            try:
                status["telegram"] = send_telegram(body)
            except Exception as exc:
                status["telegram"] = {"error": str(exc)}
            try:
                status["gmail"] = send_gmail("Email ingest watchdog restart", body)
            except Exception as exc:
                status["gmail"] = {"error": str(exc)}
            remember_notification(state, notify_key, body)
            save_json(STATE_PATH, state)
            write_status(status)

        if args.once:
            break
        time.sleep(max(args.poll_seconds, 30))


if __name__ == "__main__":
    main()
