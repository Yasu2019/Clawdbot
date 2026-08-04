#!/usr/bin/env python3
"""Bounded wait and dispatch for the minus-X thermo-fill stage."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "data/workspace/moldflow_bridge/mf_minusx_copy_results_20260801/lavie-mfminusx-thermo-fill-r11-20260804_params.json"
STATUS = ROOT / "data/state/lavie_mf_pipeline_monitor/thermo_fill_dispatch_status.json"
TRIAL_ID = "lavie-mfminusx-thermo-fill-r11-20260804"
MAX_ATTEMPTS = 900
SLEEP_SECONDS = 30

def parse_trial_verdict(output: str) -> str:
    start = output.find("{")
    if start < 0:
        return ""
    try:
        bundle, _ = json.JSONDecoder().raw_decode(output[start:])
    except json.JSONDecodeError:
        return ""
    return str((bundle.get("trial_entry") or {}).get("verdict") or "")

def classify_dispatch(returncode: int, output: str) -> tuple[str, str]:
    verdict = parse_trial_verdict(output)
    if "worker_busy" in output:
        return "waiting_worker_busy", verdict
    if returncode == 0 and verdict in ("SUCCESS", "DRY_RUN"):
        return "submitted_or_completed", verdict
    return "failed", verdict

def save(state: str, attempt: int, **detail: object) -> None:
    payload = {"updated_at": datetime.now().astimezone().isoformat(), "state": state,
               "attempt": attempt, "max_attempts": MAX_ATTEMPTS,
               "sleep_seconds": SLEEP_SECONDS, "trial_id": TRIAL_ID,
               "params_file": str(PARAMS), "detail": detail}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    temp = STATUS.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(STATUS)

def main() -> int:
    if not PARAMS.is_file():
        save("failed", 0, error="params_missing")
        return 2
    command = [sys.executable, str(ROOT / "scripts/k10_satellite_cae_dispatch.py"),
               "--category", "resin_fill_cad", "--host", "lavie",
               "--trial-id", TRIAL_ID, "--params-file", str(PARAMS),
               "--timeout", "18000", "--json"]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        save("dispatching", attempt)
        result = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True)
        output = (result.stdout or "") + (result.stderr or "")
        classification, verdict = classify_dispatch(result.returncode, output)
        if classification == "waiting_worker_busy":
            save("waiting_worker_busy", attempt, output_tail=output[-1500:])
            time.sleep(SLEEP_SECONDS)
            continue
        if classification == "submitted_or_completed":
            save("submitted_or_completed", attempt, returncode=0, verdict=verdict,
                 output_tail=output[-6000:])
            return 0
        if verdict and verdict not in ("SUCCESS", "DRY_RUN"):
            save("failed", attempt, returncode=result.returncode, verdict=verdict,
                 output_tail=output[-6000:])
            return 1
        save("failed", attempt, returncode=result.returncode, output_tail=output[-6000:])
        return result.returncode or 1
    save("timed_out", MAX_ATTEMPTS)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
