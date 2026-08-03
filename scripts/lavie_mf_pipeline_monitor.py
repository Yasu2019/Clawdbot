#!/usr/bin/env python3
"""Bounded monitor for the minus-X Moldflow/OpenFOAM pipeline."""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def evaluate(root: Path) -> dict:
    repeat = read_json(root / "data/workspace/moldflow_bridge/inc183_lavie_wait_status.json")
    tri = read_json(root / "data/workspace/apps/growth_dashboard/k10_tri_track_cae_status.json")
    old = read_json(root / "data/workspace/moldflow_bridge/mf_of_multiphysics_campaign/cool_dispatch_status.json")
    thermo = read_json(root / "data/state/lavie_mf_pipeline_monitor/thermo_fill_dispatch_status.json")
    repeat_ok = repeat.get("state") == "submitted_or_completed" and repeat.get("returncode") == 0
    old_forbidden = old.get("state") == "cancelled_by_user_sequence_change"
    phase = "waiting_pressure_repeat"
    action = "wait_for_r35_success"
    if repeat_ok and old_forbidden:
        phase, action = "ready_for_thermo_fill", "validate_and_dispatch_two_stage_thermo_fill"
    elif repeat_ok:
        phase, action = "manual_review", "review_cooling_dispatch_provenance"
    if thermo.get("state") == "waiting_worker_busy":
        phase, action = "waiting_thermo_worker", "wait_for_lavie_then_run_thermo_fill"
    elif thermo.get("state") == "submitted_or_completed":
        phase, action = "thermo_fill_completed", "verify_thermo_fields_then_build_cooling_restart"
    elif thermo.get("state") == "failed":
        phase, action = "thermo_fill_failed", "run_rca_before_retry"
    lavie = ((tri.get("tracks") or {}).get("openfoam_lavie") or {})
    return {
        "schema": "lavie.mf_pipeline_monitor.v1",
        "updated_at": datetime.now().astimezone().isoformat(),
        "monitor_ok": True, "phase": phase, "next_action": action,
        "accuracy_label": "PROXY_GAP",
        "pressure_repeat": {"trial_id": repeat.get("trial_id"), "completed_ok": repeat_ok,
                            "updated_at": repeat.get("updated_at")},
        "tri_track": {"running": bool(tri.get("running")), "last_trial": lavie.get("last"),
                      "status_updated_at": tri.get("updated_at")},
        "cooling": {"old_continuous_35s_dispatch_forbidden": old_forbidden,
                    "old_state": old.get("state"),
                    "required_workflow": "thermo_fill_then_closed_gate_cooling_restart"},
        "thermo_fill_dispatch": {"state": thermo.get("state"), "attempt": thermo.get("attempt"),
                                 "updated_at": thermo.get("updated_at"),
                                 "trial_id": thermo.get("trial_id")},
        "guards": {"observation_only": True, "does_not_stop_tri_track": True,
                   "does_not_dispatch_unvalidated_cooling": True, "bounded_monitor": True},
    }

def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for attempt in range(8):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.1 + attempt * 0.1)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--max-checks", type=int, default=2880)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    status = root / "data/state/lavie_mf_pipeline_monitor/harness_status.json"
    lock = root / "data/state/lavie_mf_pipeline_monitor/monitor.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(f"[NG] monitor lock exists: {lock}")
        return 3
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii")); os.close(descriptor)
        checks = 1 if args.once else max(1, args.max_checks)
        for index in range(1, checks + 1):
            payload = evaluate(root)
            payload["monitor"] = {"pid": os.getpid(), "check": index, "max_checks": checks,
                                  "interval_seconds": args.interval}
            atomic_write(status, payload)
            if index < checks:
                time.sleep(max(1, args.interval))
        return 0
    finally:
        try: lock.unlink()
        except FileNotFoundError: pass

if __name__ == "__main__":
    raise SystemExit(main())
