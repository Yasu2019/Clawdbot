from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "data" / "workspace" / "self_repair_three_retry_status.json"

STOP_MARKERS = [
    "AUTH_FAILED",
    "PERMISSION_DENIED",
    "APPROVAL_REQUIRED",
    "invalid api key",
    "authentication failed",
    "permission denied",
    "requires approval",
]


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def should_stop(text: str) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in STOP_MARKERS)


def write_status(payload: dict) -> None:
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="P015 bounded self-repair runner: retry a command up to 3 times.")
    parser.add_argument("--name", default="unnamed_repair")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--backoff", default="2,8,20")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        raise SystemExit("command is required after --")
    command = args.command[1:] if args.command and args.command[0] == "--" else args.command

    max_attempts = max(1, min(args.max_attempts, 3))
    backoff = [int(x.strip()) for x in args.backoff.split(",") if x.strip()]
    payload = {
        "policy_id": "P015",
        "name": args.name,
        "status": "running",
        "max_attempts": max_attempts,
        "started_at": now(),
        "attempts": [],
        "command": command,
    }
    write_status(payload)

    for attempt in range(1, max_attempts + 1):
        started = now()
        proc = subprocess.run(command, text=True, capture_output=True, shell=False)
        combined = f"{proc.stdout}\n{proc.stderr}"
        record = {
            "attempt": attempt,
            "started_at": started,
            "finished_at": now(),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
        payload["attempts"].append(record)
        if proc.returncode == 0:
            payload["status"] = "success"
            payload["finished_at"] = now()
            write_status(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        if should_stop(combined):
            payload["status"] = "stopped_fail_closed"
            payload["stop_reason"] = "auth/permission/approval/destructive-like marker detected"
            payload["finished_at"] = now()
            write_status(payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return proc.returncode or 1
        if attempt < max_attempts:
            time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])

    payload["status"] = "failed_after_3_attempts"
    payload["finished_at"] = now()
    write_status(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload["attempts"][-1]["returncode"] or 1


if __name__ == "__main__":
    raise SystemExit(main())
