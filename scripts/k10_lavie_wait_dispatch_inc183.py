# -*- coding: utf-8 -*-
"""Bounded wait-and-dispatch harness for the INC-183 pressure trial."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "data" / "workspace" / "moldflow_bridge" / "inc183_lavie_wait_status.json"
PARAMS = ROOT / "data" / "workspace" / "moldflow_bridge" / "mf_minusx_copy_results_20260801" / "lavie-mfminusx-rfc-20260801-145637_params.json"
TRIAL_ID = "lavie-mfminusx-inc183-k18066-20260803"
MAX_ATTEMPTS = 720
SLEEP_SECONDS = 30


def write_status(**values: object) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "trial_id": TRIAL_ID,
        "max_attempts": MAX_ATTEMPTS,
        "sleep_seconds": SLEEP_SECONDS,
        **values,
    }
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not PARAMS.is_file():
        write_status(state="failed", error=f"missing params: {PARAMS}")
        return 2

    command = [
        sys.executable,
        str(ROOT / "scripts" / "k10_satellite_cae_dispatch.py"),
        "--category", "resin_fill_cad",
        "--host", "lavie",
        "--trial-id", TRIAL_ID,
        "--params-file", str(PARAMS),
        "--timeout", "10800",
        "--json",
    ]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        write_status(state="dispatching", attempt=attempt)
        result = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True)
        combined = (result.stdout or "") + (result.stderr or "")
        if result.returncode == 0:
            write_status(state="submitted_or_completed", attempt=attempt, returncode=0,
                         output_tail=combined[-4000:])
            return 0
        if "worker_busy" not in combined:
            write_status(state="failed", attempt=attempt, returncode=result.returncode,
                         output_tail=combined[-4000:])
            return result.returncode or 1
        write_status(state="waiting_worker_busy", attempt=attempt,
                     next_retry_seconds=SLEEP_SECONDS, output_tail=combined[-1200:])
        time.sleep(SLEEP_SECONDS)

    write_status(state="timed_out", attempt=MAX_ATTEMPTS)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
