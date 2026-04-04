from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def discover_repo_root() -> Path:
    for candidate in [Path.cwd(), Path("D:/Clawdbot_Docker_20260125"), Path("E:/ClawstackData")]:
        resolved = candidate.resolve()
        if (resolved / "AGENTS.md").exists() and (resolved / "data" / "workspace").exists():
            return resolved
    raise FileNotFoundError("Could not locate repository root.")


ROOT = discover_repo_root()
WORKSPACE = ROOT / "data" / "workspace"
STATE_DIR = ROOT / "data" / "state" / "ollama_pull"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def write_status(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull an Ollama model inside the native Docker ollama container with progress status.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--container", default="clawstack-unified-ollama-1")
    parser.add_argument("--stale-seconds", type=int, default=600)
    args = parser.parse_args()

    status_path = WORKSPACE / "ollama_pull_status.json"
    harness_path = STATE_DIR / "harness_status.json"
    log_path = WORKSPACE / "ollama_pull.log"

    cmd = [
        "wsl.exe",
        "-d",
        "Ubuntu",
        "-e",
        "sh",
        "-lc",
        (
            "env DOCKER_HOST=unix:///var/run/docker-native.sock "
            f"docker exec {args.container} ollama pull {args.model}"
        ),
    ]

    started = iso_now()
    base = {
        "updatedAt": started,
        "startedAt": started,
        "model": args.model,
        "container": args.container,
        "command": cmd,
    }
    write_status(status_path, {**base, "state": "starting"})
    write_status(harness_path, {**base, "status": "starting"})

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    last_line = ""
    last_progress_at = time.time()
    with log_path.open("a", encoding="utf-8") as log_file:
        while True:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                clean = line.rstrip("\r\n")
                last_line = clean
                last_progress_at = time.time()
                log_file.write(clean + "\n")
                log_file.flush()
                payload = {
                    **base,
                    "updatedAt": iso_now(),
                    "state": "running",
                    "lastOutput": clean,
                    "pid": proc.pid,
                }
                write_status(status_path, payload)
                write_status(harness_path, {**payload, "status": "running"})
            elif proc.poll() is not None:
                break
            else:
                now = time.time()
                state = "running"
                if now - last_progress_at > args.stale_seconds:
                    state = "stale"
                payload = {
                    **base,
                    "updatedAt": iso_now(),
                    "state": state,
                    "lastOutput": last_line,
                    "pid": proc.pid,
                }
                write_status(status_path, payload)
                write_status(harness_path, {**payload, "status": state})
                time.sleep(2)

    returncode = proc.wait()
    finished = iso_now()
    final_state = "completed" if returncode == 0 else "failed"
    payload = {
        **base,
        "updatedAt": finished,
        "finishedAt": finished,
        "state": final_state,
        "returncode": returncode,
        "lastOutput": last_line,
        "pid": proc.pid,
    }
    write_status(status_path, payload)
    write_status(harness_path, {**payload, "status": final_state})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
