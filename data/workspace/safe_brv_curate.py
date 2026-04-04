#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
QUEUE_PATH = WORKSPACE / "byterover_curate_queue.jsonl"
STATUS_PATH = WORKSPACE / "byterover_curate_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run_command(command: list[str], timeout_seconds: int = 30) -> dict:
    executable = shutil.which(command[0]) or shutil.which(f"{command[0]}.cmd")
    final_command = [executable, *command[1:]] if executable else command
    try:
        proc = subprocess.run(
            final_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(final_command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(final_command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def is_logged_in(status_output: str) -> bool:
    normalized = status_output.lower()
    return "account: not connected" not in normalized


def append_queue(entry: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe wrapper around brv curate with local fallback queue.")
    parser.add_argument("context", help="Curate context text")
    parser.add_argument("-f", "--file", action="append", default=[], help="Project-scoped file paths")
    args = parser.parse_args()

    status = {
        "updatedAt": now_jst_text(),
        "service": "safe_brv_curate",
        "contextPreview": args.context[:200],
        "files": args.file[:5],
    }

    status_check = run_command(["brv", "status"], timeout_seconds=20)
    status["statusCheck"] = status_check
    logged_in = is_logged_in(status_check.get("stdout", ""))
    status["loggedIn"] = logged_in

    command = ["brv", "curate", args.context]
    for file_path in args.file[:5]:
        command.extend(["-f", file_path])

    if not logged_in:
        queue_entry = {
            "queuedAt": now_jst_text(),
            "reason": "not_logged_in",
            "context": args.context,
            "files": args.file[:5],
        }
        append_queue(queue_entry)
        status["result"] = "queued_locally"
        status["reason"] = "ByteRover account is not connected"
        status["queuePath"] = str(QUEUE_PATH)
        write_status(status)
        print(json.dumps(status, ensure_ascii=True))
        return

    curate_result = run_command(command, timeout_seconds=60)
    status["curateResult"] = curate_result

    combined = f"{curate_result.get('stdout', '')}\n{curate_result.get('stderr', '')}".lower()
    auth_failure = (
        "authentication required for cloud sync" in combined
        or "request failed with status code 401" in combined
        or curate_result.get("returncode") not in (0, None)
    )

    if auth_failure:
        queue_entry = {
            "queuedAt": now_jst_text(),
            "reason": "curate_auth_failure",
            "context": args.context,
            "files": args.file[:5],
            "curateResult": curate_result,
        }
        append_queue(queue_entry)
        status["result"] = "queued_after_auth_failure"
        status["reason"] = "brv curate failed; saved to local queue"
        status["queuePath"] = str(QUEUE_PATH)
    else:
        status["result"] = "curated"
        status["reason"] = "brv curate completed successfully"

    write_status(status)
    print(json.dumps(status, ensure_ascii=True))


if __name__ == "__main__":
    main()
