#!/usr/bin/env python3
"""Monitor INC-187 r19 staged startup and promote r20 -> r21 -> r22 full fill."""
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
sys.path.insert(0, str(ROOT / "scripts"))

TRIAL_R19 = "lavie-mfminusx-thermo-startup-r19-20260805"
TRIAL_R20 = "lavie-mfminusx-thermo-startup-r20-20260805"
TRIAL_R21 = "lavie-mfminusx-thermo-startup-r21-20260805"
TRIAL_R22 = "lavie-mfminusx-thermo-fill-r22-20260805"
LEDGER = ROOT / "data" / "workspace" / "satellite_cae_log.jsonl"
STATE = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor" / "inc187_r19_autopromote_status.json"
PARAMS_DIR = ROOT / "data" / "workspace" / "moldflow_bridge" / "mf_minusx_copy_results_20260801"
PARAMS_R19 = PARAMS_DIR / f"{TRIAL_R19}_params.json"
INTERVAL_SECONDS = 30
MAX_CHECKS = 2880
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
        "r19_trial": TRIAL_R19,
        "r20_trial": TRIAL_R20,
        "r21_trial": TRIAL_R21,
        "r22_trial": TRIAL_R22,
        "accuracy_label": "PROXY_GAP",
        "details": details,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(STATE)


def notify(text: str) -> None:
    try:
        import cae_telegram_video_notify as tg

        tg.send_telegram_message(text)
    except Exception as exc:
        print(f"[notify] non-fatal: {exc}", flush=True)


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


def startup_passes(trial: dict, min_time_s: float) -> tuple[bool, dict]:
    defects = trial.get("defects_detected") or {}
    latest_time = float(defects.get("fill_time_s") or 0.0)
    t_min = defects.get("T_min")
    t_max = defects.get("T_max")
    evidence = {
        "latest_time_s": latest_time,
        "T_min_K": t_min,
        "T_max_K": t_max,
        "verdict": trial.get("verdict"),
        "min_time_s": min_time_s,
    }
    if trial.get("verdict") != "SUCCESS":
        return False, evidence
    if latest_time + 1e-12 < min_time_s:
        return False, evidence
    if t_min is None or t_max is None:
        return False, evidence
    return 250.0 <= float(t_min) <= float(t_max) <= 600.0, evidence


def write_params(src: Path, dest: Path, updates: dict) -> None:
    params = json.loads(src.read_text(encoding="utf-8-sig"))
    params.update(updates)
    temporary = dest.with_suffix(".tmp")
    temporary.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(dest)


def dispatch(trial_id: str, params_path: Path, timeout: int) -> tuple[int, str]:
    command = [
        sys.executable,
        "-u",
        str(ROOT / "scripts" / "k10_satellite_cae_dispatch.py"),
        "--category",
        "resin_fill_cad",
        "--host",
        "lavie",
        "--trial-id",
        trial_id,
        "--params-file",
        str(params_path),
        "--timeout",
        str(timeout),
        "--json",
    ]
    result = subprocess.run(
        command, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout + 180
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def wait_for_trial(trial_id: str, min_time_s: float, check_start: int, label: str):
    for check in range(check_start, MAX_CHECKS + 1):
        trial = latest_trial(trial_id)
        if trial is None:
            save(f"monitoring_{label}", check)
            time.sleep(INTERVAL_SECONDS)
            continue
        verdict = str(trial.get("verdict") or "")
        passed, evidence = startup_passes(trial, min_time_s)
        if verdict not in {"SUCCESS", "FAILED", "TIMEOUT", "ERROR", "PREGATE_FAIL", "FAILED_NONPHYSICAL"}:
            save(f"monitoring_{label}", check, evidence=evidence)
            time.sleep(INTERVAL_SECONDS)
            continue
        if not passed:
            save(
                f"{label}_failed_or_not_promotable",
                check,
                verdict=verdict,
                failure_tags=trial.get("failure_tags") or [],
                evidence=evidence,
                next_action="RCA before a fresh ID; no blind retry",
            )
            notify(f"[INC-187] {trial_id} not promotable verdict={verdict} evidence={evidence}")
            return check, trial, evidence, False
        return check, trial, evidence, True
    save("monitor_timeout", MAX_CHECKS, trial_id=trial_id)
    notify(f"[INC-187] monitor timeout waiting for {trial_id}")
    return MAX_CHECKS, None, {}, False


def main() -> int:
    if not PARAMS_R19.is_file():
        save("blocked_missing_r19_params", 0)
        notify("[INC-187] blocked: missing r19 params")
        return 2
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        check, trial, evidence, ok = wait_for_trial(TRIAL_R19, 1.9e-5, 1, "r19")
        if not ok:
            return 1

        p20 = PARAMS_DIR / f"{TRIAL_R20}_params.json"
        write_params(
            PARAMS_R19,
            p20,
            {
                "analysis_end_time_s": 0.0001,
                "cool_end_time": 0.0001,
                "write_interval_s": 2e-5,
                "trial_purpose": "INC-187 r20 extend r19-stable numerics to endTime 1e-4",
                "predecessor_trial": TRIAL_R19,
                "thermal_startup_smoke": True,
            },
        )
        save("dispatching_r20", check, evidence=evidence)
        notify(f"[INC-187] r19 PASS -> {TRIAL_R20}")
        dispatch(TRIAL_R20, p20, 28800)
        check, trial, evidence, ok = wait_for_trial(TRIAL_R20, 9.9e-5, check + 1, "r20")
        if not ok:
            return 1

        p21 = PARAMS_DIR / f"{TRIAL_R21}_params.json"
        write_params(
            p20,
            p21,
            {
                "analysis_end_time_s": 0.001,
                "cool_end_time": 0.001,
                "write_interval_s": 0.0002,
                "trial_purpose": "INC-187 r21 extend to endTime 0.001",
                "predecessor_trial": TRIAL_R20,
                "thermal_startup_smoke": True,
            },
        )
        save("dispatching_r21", check, evidence=evidence)
        notify(f"[INC-187] r20 PASS -> {TRIAL_R21}")
        dispatch(TRIAL_R21, p21, 43200)
        check, trial, evidence, ok = wait_for_trial(TRIAL_R21, 0.000999, check + 1, "r21")
        if not ok:
            return 1

        p22 = PARAMS_DIR / f"{TRIAL_R22}_params.json"
        write_params(
            p21,
            p22,
            {
                "analysis_end_time_s": 1.230131,
                "cool_end_time": 1.230131,
                "write_interval_s": 0.05,
                "inlet_velocity": 12.0,
                "inlet_velocity_xyz": [-12.0, 0.0, 0.0],
                "thermal_startup_smoke": False,
                "trial_purpose": "INC-187 r22 full thermo fill after staged startups",
                "predecessor_trial": TRIAL_R21,
            },
        )
        save("dispatching_r22_full_fill", check, evidence=evidence)
        notify(f"[INC-187] r21 PASS -> {TRIAL_R22}")
        rc, output = dispatch(TRIAL_R22, p22, 18000)
        trial22 = latest_trial(TRIAL_R22)
        verdict = str((trial22 or {}).get("verdict") or "")
        state = "r22_full_fill_complete" if rc == 0 and verdict == "SUCCESS" else "r22_full_fill_failed"
        save(state, check, verdict=verdict, returncode=rc, output_tail=output[-4000:])
        notify(f"[INC-187] {TRIAL_R22} finished verdict={verdict} state={state}")
        return 0 if state.endswith("complete") else 1
    finally:
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    raise SystemExit(main())
