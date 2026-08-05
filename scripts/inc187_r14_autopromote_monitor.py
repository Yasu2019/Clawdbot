#!/usr/bin/env python3
"""Monitor INC-187 r14 startup and promote a verified run to full-fill r15."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import ctypes
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL_R14 = "lavie-mfminusx-thermo-startup-r14-20260805"
TRIAL_R15 = "lavie-mfminusx-thermo-fill-r15-20260805"
LEDGER = ROOT / "data" / "workspace" / "satellite_cae_log.jsonl"
STATE = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor" / "inc187_r14_autopromote_status.json"
PARAMS_R14 = (
    ROOT
    / "data"
    / "workspace"
    / "moldflow_bridge"
    / "mf_minusx_copy_results_20260801"
    / f"{TRIAL_R14}_params.json"
)
PARAMS_R15 = PARAMS_R14.with_name(f"{TRIAL_R15}_params.json")
INTERVAL_SECONDS = 30
MAX_CHECKS = 1920
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def save(state: str, check: int, **details: object) -> None:
    payload = {
        "schema": "clawstack.inc187.autopromote.v1",
        "updated_at": datetime.now().astimezone().isoformat(),
        "state": state,
        "check": check,
        "max_checks": MAX_CHECKS,
        "interval_seconds": INTERVAL_SECONDS,
        "r14_trial": TRIAL_R14,
        "r15_trial": TRIAL_R15,
        "accuracy_label": "PROXY_GAP",
        "details": details,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE)


def latest_trial(trial_id: str) -> dict | None:
    if not LEDGER.exists():
        return None
    found = None
    for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        if trial_id not in line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        trial = row.get("trial_entry") or {}
        if trial.get("id") == trial_id:
            found = trial
    return found


def startup_passes(trial: dict) -> tuple[bool, dict]:
    defects = trial.get("defects_detected") or {}
    latest_time = float(defects.get("fill_time_s") or 0.0)
    t_min = defects.get("T_min")
    t_max = defects.get("T_max")
    evidence = {
        "latest_time_s": latest_time,
        "T_min_K": t_min,
        "T_max_K": t_max,
        "verdict": trial.get("verdict"),
    }
    if trial.get("verdict") != "SUCCESS":
        return False, evidence
    if latest_time < 0.000999:
        return False, evidence
    if t_min is None or t_max is None:
        return False, evidence
    return 250.0 <= float(t_min) <= float(t_max) <= 600.0, evidence


def write_r15_params() -> None:
    params = json.loads(PARAMS_R14.read_text(encoding="utf-8-sig"))
    params.update(
        {
            "analysis_end_time_s": 1.230131,
            "cool_end_time": 1.230131,
            "write_interval_s": 0.05,
            "trial_purpose": "INC-187 r15 full thermo fill promoted from verified r14 startup",
            "predecessor_trial": TRIAL_R14,
            "promotion_rule": "require SUCCESS, fill completion, bounded T, then closed-gate cooling restart",
            "accuracy_band_label": "PROXY_GAP",
        }
    )
    temporary = PARAMS_R15.with_suffix(".tmp")
    temporary.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(PARAMS_R15)


def dispatch_r15(check: int, startup_evidence: dict) -> int:
    write_r15_params()
    save("dispatching_r15_full_fill", check, startup_evidence=startup_evidence, params=str(PARAMS_R15))
    command = [
        sys.executable,
        str(ROOT / "scripts" / "k10_satellite_cae_dispatch.py"),
        "--category",
        "resin_fill_cad",
        "--host",
        "lavie",
        "--trial-id",
        TRIAL_R15,
        "--params-file",
        str(PARAMS_R15),
        "--timeout",
        "18000",
        "--json",
    ]
    result = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True, timeout=18120)
    output = (result.stdout or "") + (result.stderr or "")
    trial = latest_trial(TRIAL_R15)
    verdict = str((trial or {}).get("verdict") or "")
    state = "r15_full_fill_complete" if result.returncode == 0 and verdict == "SUCCESS" else "r15_full_fill_failed"
    save(
        state,
        check,
        startup_evidence=startup_evidence,
        verdict=verdict,
        returncode=result.returncode,
        output_tail=output[-6000:],
    )
    return 0 if state == "r15_full_fill_complete" else 1


def main() -> int:
    if not PARAMS_R14.is_file():
        save("blocked_missing_r14_params", 0, params=str(PARAMS_R14))
        return 2
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        for check in range(1, MAX_CHECKS + 1):
            trial = latest_trial(TRIAL_R14)
            if trial is None:
                save("monitoring_r14", check)
                time.sleep(INTERVAL_SECONDS)
                continue
            passed, evidence = startup_passes(trial)
            if not passed:
                if trial.get("verdict") in {None, ""}:
                    save("monitoring_r14", check, evidence=evidence)
                    time.sleep(INTERVAL_SECONDS)
                    continue
                save(
                    "r14_failed_or_not_promotable",
                    check,
                    verdict=trial.get("verdict"),
                    failure_tags=trial.get("failure_tags") or [],
                    evidence=evidence,
                    next_action="RCA before a fresh ID; no blind retry",
                )
                return 1
            return dispatch_r15(check, evidence)
        save("monitor_timeout", MAX_CHECKS, next_action="manual status audit")
        return 1
    finally:
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    raise SystemExit(main())
