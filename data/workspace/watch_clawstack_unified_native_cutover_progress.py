from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path.cwd()
STATUS_PATH = REPO_ROOT / "data/workspace/prepare_clawstack_unified_native_cutover_status.json"
WATCH_STATUS_PATH = REPO_ROOT / "data/workspace/clawstack_unified_native_cutover_progress_watchdog_status.json"
UPDATE_SCRIPT = REPO_ROOT / "data/workspace/update_clawstack_unified_native_cutover_progress.py"


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def python_pids() -> list[int]:
    cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '^python' -and $_.CommandLine -and $_.CommandLine -like '*prepare_clawstack_unified_native_cutover.py*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def load_phase() -> str | None:
    if not STATUS_PATH.exists():
        return None
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8")).get("phase")
    except Exception:
        return None


def write_watch_status(state: str, pids: list[int]) -> None:
    payload = {
        "updatedAt": iso_now(),
        "state": state,
        "trackedPids": pids,
        "statusPath": str(STATUS_PATH),
        "progressUpdater": str(UPDATE_SCRIPT),
    }
    WATCH_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_update() -> None:
    subprocess.run(
        ["python", str(UPDATE_SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    while True:
        pids = python_pids()
        phase = load_phase()
        run_update()
        state = "watching" if pids else "idle"
        if phase == "prewarm_completed" and not pids:
            state = "completed"
        write_watch_status(state, pids)
        if state == "completed":
            return 0
        time.sleep(15)


if __name__ == "__main__":
    raise SystemExit(main())
