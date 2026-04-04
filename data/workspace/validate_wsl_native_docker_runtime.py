from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from docker_runtime import describe_docker_runtime, docker_command


WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "wsl_native_docker_validation_status.json"


def run_command(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def main() -> int:
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    status: dict = {
        "timestamp": ts,
        "runtime": describe_docker_runtime(),
        "ok": False,
        "dockerVersion": None,
        "dockerInfo": None,
        "sampleContainers": [],
        "error": None,
    }
    try:
        rc, out, err = run_command(docker_command("version", "--format", "{{.Server.Version}}"))
        if rc != 0:
            raise RuntimeError(err or out or "docker version failed")
        status["dockerVersion"] = out

        rc, out, err = run_command(docker_command("info", "--format", "{{json .}}"))
        if rc != 0:
            raise RuntimeError(err or out or "docker info failed")
        status["dockerInfo"] = json.loads(out)

        rc, out, err = run_command(docker_command("ps", "--format", "{{.Names}}"))
        if rc != 0:
            raise RuntimeError(err or out or "docker ps failed")
        status["sampleContainers"] = out.splitlines()[:10]
        status["ok"] = True
    except Exception as exc:
        status["error"] = str(exc)

    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
