# -*- coding: utf-8 -*-
"""Bounded, non-invasive wait-and-dispatch harness for minus-X Cool trial."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_satellite_cae_dispatch as dispatch
import k10_satellite_dispatch as sjp

PARAMS = ROOT / "data/workspace/moldflow_bridge/mf_of_multiphysics_campaign/lavie_mfminusx_cool_urgent01_params.json"
STATUS = ROOT / "data/workspace/moldflow_bridge/mf_of_multiphysics_campaign/cool_dispatch_status.json"
TRIAL_ID = "lavie-mfminusx-cool-20260802-urgent02"
MAX_ATTEMPTS = 240
SLEEP_SECONDS = 30


def save(state: str, attempt: int, detail: dict | None = None) -> None:
    STATUS.write_text(json.dumps({
        "updated_at": datetime.now().astimezone().isoformat(),
        "state": state, "attempt": attempt, "max_attempts": MAX_ATTEMPTS,
        "sleep_seconds": SLEEP_SECONDS, "trial_id": TRIAL_ID,
        "params_file": str(PARAMS).replace("\\", "/"), "detail": detail or {},
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    params = json.loads(PARAMS.read_text(encoding="utf-8"))
    token = sjp.load_token()
    cfg = router.load_config()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        save("dispatch_attempt", attempt)
        bundle = dispatch.run_lavie_trial(
            node="lavie", category="resin_fill_cad", params=params,
            trial_id=TRIAL_ID, dry_run=False, timeout=18000, token=token, cfg=cfg,
        )
        worker = bundle.get("worker_result") or {}
        if worker.get("status") == "busy" or worker.get("error") == "worker_busy":
            save("waiting_worker_busy", attempt, {"worker_status": "busy"})
            time.sleep(SLEEP_SECONDS)
            continue
        trial = bundle.get("trial_entry") or {}
        save("completed" if trial.get("verdict") == "SUCCESS" else "finished_non_success", attempt, {
            "worker_status": worker.get("status"), "verdict": trial.get("verdict"),
            "error": trial.get("error"), "run_dir": trial.get("run_dir"),
            "log_snippet": trial.get("log_snippet"),
            "stdout_tail": worker.get("stdout_tail"),
            "stderr_tail": worker.get("stderr_tail"),
        })
        dispatch.merge_trial_into_log(trial)
        dispatch.append_cae_log({"source": "wait_dispatch_mfminusx_cool", "trial_entry": trial})
        return 0 if trial.get("verdict") == "SUCCESS" else 1
    save("gave_up_busy", MAX_ATTEMPTS)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
