#!/usr/bin/env python3
"""Monitor INC-187 r16 staged startup and promote to r17 then r18 full fill."""
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

TRIAL_R16 = "lavie-mfminusx-thermo-startup-r16-20260805"
TRIAL_R17 = "lavie-mfminusx-thermo-startup-r17-20260805"
TRIAL_R18 = "lavie-mfminusx-thermo-fill-r18-20260805"
LEDGER = ROOT / "data" / "workspace" / "satellite_cae_log.jsonl"
STATE = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor" / "inc187_r16_autopromote_status.json"
PARAMS_DIR = ROOT / "data" / "workspace" / "moldflow_bridge" / "mf_minusx_copy_results_20260801"
PARAMS_R16 = PARAMS_DIR / f"{TRIAL_R16}_params.json"
PARAMS_R17 = PARAMS_DIR / f"{TRIAL_R17}_params.json"
PARAMS_R18 = PARAMS_DIR / f"{TRIAL_R18}_params.json"
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
        "r16_trial": TRIAL_R16,
        "r17_trial": TRIAL_R17,
        "r18_trial": TRIAL_R18,
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


def dispatch(trial_id: str, params_path: Path, timeout: int) -> tuple[int, str, dict | None]:
    command = [
        sys.executable,
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
        command,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=timeout + 180,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output, latest_trial(trial_id)


def wait_for_trial(trial_id: str, min_time_s: float, check_start: int) -> tuple[int, dict | None, dict]:
    for check in range(check_start, MAX_CHECKS + 1):
        trial = latest_trial(trial_id)
        if trial is None:
            save(f"monitoring_{trial_id.split('-')[-2]}", check)
            time.sleep(INTERVAL_SECONDS)
            continue
        passed, evidence = startup_passes(trial, min_time_s)
        if trial.get("verdict") not in {"SUCCESS", "FAILED", "TIMEOUT", "ERROR", "PREGATE_FAIL"}:
            save(f"monitoring_{trial_id.split('-')[-2]}", check, evidence=evidence)
            time.sleep(INTERVAL_SECONDS)
            continue
        if not passed:
            save(
                f"{trial_id.split('-')[-2]}_failed_or_not_promotable",
                check,
                verdict=trial.get("verdict"),
                failure_tags=trial.get("failure_tags") or [],
                evidence=evidence,
                next_action="RCA before a fresh ID; no blind retry",
            )
            notify(
                f"[INC-187] {trial_id} not promotable\n"
                f"verdict={trial.get('verdict')} tags={trial.get('failure_tags')}\n"
                f"evidence={json.dumps(evidence, ensure_ascii=False)}"
            )
            return check, trial, evidence
        return check, trial, evidence
    save("monitor_timeout", MAX_CHECKS, trial_id=trial_id)
    notify(f"[INC-187] monitor timeout waiting for {trial_id}")
    return MAX_CHECKS, None, {}


def main() -> int:
    if not PARAMS_R16.is_file():
        save("blocked_missing_r16_params", 0, params=str(PARAMS_R16))
        notify("[INC-187] blocked: missing r16 params")
        return 2
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        check, trial, evidence = wait_for_trial(TRIAL_R16, 9.9e-5, 1)
        if trial is None or not startup_passes(trial, 9.9e-5)[0]:
            return 1

        write_params(
            PARAMS_R16,
            PARAMS_R17,
            {
                "analysis_end_time_s": 0.001,
                "cool_end_time": 0.001,
                "write_interval_s": 0.0002,
                "inlet_velocity": 6.0,
                "inlet_velocity_xyz": [-6.0, 0.0, 0.0],
                "thermal_startup_smoke": True,
                "trial_purpose": "INC-187 r17 extend verified r16 numerics to endTime 0.001",
                "predecessor_trial": TRIAL_R16,
                "promotion_rule": "SUCCESS+latest>=0.001+bounded T -> r18 full fill",
            },
        )
        save("dispatching_r17", check, startup_evidence=evidence, params=str(PARAMS_R17))
        notify(f"[INC-187] r16 PASS -> dispatching {TRIAL_R17}")
        rc, output, _ = dispatch(TRIAL_R17, PARAMS_R17, 28800)
        check2, trial17, evidence17 = wait_for_trial(TRIAL_R17, 0.000999, check + 1)
        if trial17 is None or not startup_passes(trial17, 0.000999)[0]:
            save(
                "r17_failed_or_not_promotable",
                check2,
                r17_returncode=rc,
                evidence=evidence17,
                output_tail=output[-4000:],
            )
            return 1

        write_params(
            PARAMS_R17,
            PARAMS_R18,
            {
                "analysis_end_time_s": 1.230131,
                "cool_end_time": 1.230131,
                "write_interval_s": 0.05,
                "inlet_velocity": 12.0,
                "inlet_velocity_xyz": [-12.0, 0.0, 0.0],
                "thermal_startup_smoke": False,
                "trial_purpose": "INC-187 r18 full thermo fill after staged r16/r17 startup",
                "predecessor_trial": TRIAL_R17,
                "promotion_rule": "full fill then closed-gate cooling restart",
            },
        )
        save("dispatching_r18_full_fill", check2, startup_evidence=evidence17, params=str(PARAMS_R18))
        notify(f"[INC-187] r17 PASS -> dispatching {TRIAL_R18}")
        rc18, output18, trial18 = dispatch(TRIAL_R18, PARAMS_R18, 18000)
        verdict = str((trial18 or {}).get("verdict") or "")
        state = "r18_full_fill_complete" if rc18 == 0 and verdict == "SUCCESS" else "r18_full_fill_failed"
        save(state, check2, verdict=verdict, returncode=rc18, output_tail=output18[-6000:])
        notify(f"[INC-187] {TRIAL_R18} finished verdict={verdict} state={state}")
        return 0 if state == "r18_full_fill_complete" else 1
    finally:
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    raise SystemExit(main())
