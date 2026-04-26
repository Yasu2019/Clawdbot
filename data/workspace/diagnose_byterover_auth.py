#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "byterover_auth_diagnostic_status.json"


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


def main() -> None:
    status = {
        "generatedAt": now_jst_text(),
        "service": "byterover_auth_diagnostics",
    }
    status["brvStatus"] = run_command(["brv", "status"], 20)
    status["providers"] = run_command(["brv", "providers"], 20)
    status["model"] = run_command(["brv", "model"], 20)
    status["loginHelp"] = run_command(["brv", "login", "--help"], 20)
    status["sampleCurate"] = run_command(["brv", "curate", "ByteRover auth diagnostic probe"], 30)

    combined = (
        status["sampleCurate"].get("stdout", "")
        + "\n"
        + status["sampleCurate"].get("stderr", "")
    ).lower()
    status["findings"] = {
        "accountConnected": "account: not connected" not in status["brvStatus"].get("stdout", "").lower(),
        "usesByteRoverProvider": "provider: byterover" in status["providers"].get("stdout", "").lower(),
        "sampleCurateAuthFailure": (
            "authentication required for cloud sync" in combined
            or "status code 401" in combined
        ),
    }
    status["summary"] = (
        "ByteRover CLI can run locally, but curate currently fails with authentication/cloud-sync style errors."
        if status["findings"]["sampleCurateAuthFailure"]
        else "No authentication failure was reproduced during the sample curate."
    )

    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=True))


if __name__ == "__main__":
    main()
