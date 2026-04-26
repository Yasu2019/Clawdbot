#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "wsl_distro_keepalive_status.json"
HARNESS_PATH = ROOT / "data" / "state" / "wsl_distro_keepalive" / "harness_status.json"


def now_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def launch_keepalive(distro: str) -> subprocess.Popen[str]:
    command = [
        "wsl.exe",
        "-d",
        distro,
        "--",
        "bash",
        "-lc",
        "trap 'exit 0' TERM INT; while true; do sleep 300; done",
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep WSL distro alive for native Docker services.")
    parser.add_argument("--distro", default="Ubuntu")
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    child: subprocess.Popen[str] | None = None
    restart_count = 0
    started_at = now_text()

    while True:
        reason = "healthy"
        if child is None or child.poll() is not None:
            if child is not None:
                restart_count += 1
                reason = "restarted_after_exit"
            else:
                reason = "started"
            child = launch_keepalive(args.distro)

        status = {
            "service": "wsl_distro_keepalive",
            "startedAt": started_at,
            "updatedAt": now_text(),
            "stage": "running",
            "reason": reason,
            "distro": args.distro,
            "pollSeconds": args.poll_seconds,
            "restartCount": restart_count,
            "childPid": child.pid if child else None,
        }
        write_json(STATUS_PATH, status)
        write_json(HARNESS_PATH, status)
        time.sleep(max(5, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
