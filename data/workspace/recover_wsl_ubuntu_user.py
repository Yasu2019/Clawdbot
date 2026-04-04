from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "recover_wsl_ubuntu_user_status.json"


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(command: list[str], timeout_ms: int = 30000) -> dict:
    proc = subprocess.run(
        command,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_ms / 1000,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def main() -> int:
    status = {"startedAt": iso_now(), "steps": []}
    status["steps"].append(run(["wsl", "--shutdown"], 20000))
    status["steps"].append(run(["wsl", "--manage", "Ubuntu", "--set-default-user", "root"], 60000))
    root_probe = run(["wsl", "-d", "Ubuntu", "-u", "root", "--", "bash", "-lc", "whoami && id -u"], 20000)
    status["steps"].append(root_probe)
    status["steps"].append(run(["wsl", "--manage", "Ubuntu", "--set-default-user", "yasu"], 60000))
    user_probe = run(["wsl", "-d", "Ubuntu", "--", "bash", "-lc", "whoami && id -u"], 20000)
    status["steps"].append(user_probe)
    status["finishedAt"] = iso_now()
    status["ok"] = root_probe["returncode"] == 0 and user_probe["returncode"] == 0
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
