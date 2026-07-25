import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import datetime
import json
import os
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

os.environ.setdefault("CAE_OPENRADIOSS_NTHREAD", "2")
os.environ.setdefault("CAE_SKIP_RUN_CLEANUP", "1")

import cae_te_engine


TRIAL_ID = "k10-openradioss-4mmx4mm-spm80-20260725-v3"
PARAMS_PATH = ROOT / "data" / "workspace" / "openradioss_urgent_k10" / "params_spm80.json"
STATUS_PATH = ROOT / "data" / "workspace" / "openradioss_urgent_k10" / "harness_status_spm80.json"
RESULT_PATH = ROOT / "data" / "workspace" / "openradioss_urgent_k10" / "result_spm80.json"


def now_jst() -> str:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def heartbeat(stop_event: threading.Event, state: dict) -> None:
    while not stop_event.wait(60):
        state["heartbeat_at"] = now_jst()
        state["elapsed_sec"] = round(time.monotonic() - state["_started_monotonic"], 1)
        write_json(STATUS_PATH, {key: value for key, value in state.items() if not key.startswith("_")})


def parse_part_z_displacement(vtk_path: Path, part_id: int) -> dict:
    lines = vtk_path.read_text(encoding="ascii", errors="replace").splitlines()
    points_index = next(i for i, line in enumerate(lines) if line.startswith("POINTS "))
    point_count = int(lines[points_index].split()[1])
    cells_index = next(i for i, line in enumerate(lines) if line.startswith("CELLS "))
    cell_count = int(lines[cells_index].split()[1])
    cells: list[list[int]] = []
    for line in lines[cells_index + 1 : cells_index + 1 + cell_count]:
        values = [int(value) for value in line.split()]
        cells.append(values[1 : 1 + values[0]])
    vector_index = next(
        i for i, line in enumerate(lines) if line.startswith("VECTORS Displacement")
    )
    displacements = [
        [float(value) for value in line.split()]
        for line in lines[vector_index + 1 : vector_index + 1 + point_count]
    ]
    part_index = next(i for i, line in enumerate(lines) if line.startswith("SCALARS PART_ID"))
    part_values = [
        int(float(lines[part_index + 2 + offset].strip()))
        for offset in range(cell_count)
    ]
    nodes = sorted(
        {
            node
            for cell, current_part in zip(cells, part_values)
            if current_part == part_id
            for node in cell
        }
    )
    z_values_mm = [displacements[node][2] * 1000.0 for node in nodes]
    if not z_values_mm:
        raise ValueError(f"part {part_id} has no VTK nodes")
    return {
        "part_id": part_id,
        "node_count": len(nodes),
        "z_min_mm": min(z_values_mm),
        "z_max_mm": max(z_values_mm),
        "z_mean_mm": sum(z_values_mm) / len(z_values_mm),
    }


def main() -> int:
    params = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
    state = {
        "trial_id": TRIAL_ID,
        "phase": "running",
        "started_at": now_jst(),
        "heartbeat_at": now_jst(),
        "pid": os.getpid(),
        "requirements": {
            "spm": 80.0,
            "press_stroke_mm": 80.0,
            "punch_z_mm": -2.0,
            "stripper_z_mm": -0.19,
        },
        "_started_monotonic": time.monotonic(),
    }
    write_json(STATUS_PATH, {key: value for key, value in state.items() if not key.startswith("_")})
    stop_event = threading.Event()
    monitor = threading.Thread(target=heartbeat, args=(stop_event, state), daemon=True)
    monitor.start()
    try:
        entry = cae_te_engine.run_single_trial(
            exp_id="OR-BLANK-ASSY-001",
            params=params,
            trial_id=TRIAL_ID,
            dry_run=False,
            timeout=345600,
            skip_resource_check=True,
            append_log=True,
            host="k10",
        )
        run_dir = Path(entry.get("run_dir") or "")
        vtk_files = sorted(run_dir.glob("*.vtk")) if run_dir.is_dir() else []
        displacement_kpis: dict = {}
        displacement_reasons: list[str] = []
        if vtk_files:
            final_vtk = vtk_files[-1]
            punch = parse_part_z_displacement(final_vtk, 1)
            stripper = parse_part_z_displacement(final_vtk, 4)
            displacement_kpis = {
                "vtk": str(final_vtk),
                "punch": punch,
                "stripper": stripper,
            }
            if abs(punch["z_mean_mm"] - (-2.0)) > 0.01:
                displacement_reasons.append(
                    f"punch_z_mm={punch['z_mean_mm']:.6f} outside -2.00+/-0.01"
                )
            if abs(stripper["z_mean_mm"] - (-0.19)) > 0.005:
                displacement_reasons.append(
                    f"stripper_z_mm={stripper['z_mean_mm']:.6f} outside -0.190+/-0.005"
                )
        else:
            displacement_reasons.append("missing_vtk")
        final_verdict = entry.get("verdict")
        if displacement_reasons:
            final_verdict = "FAILED_DISPLACEMENT_GATE"
        result = {
            "trial": entry,
            "displacement_kpis": displacement_kpis,
            "displacement_gate_reasons": displacement_reasons,
            "final_verdict": final_verdict,
            "completed_at": now_jst(),
        }
        write_json(RESULT_PATH, result)
        state.update(
            {
                "phase": "done",
                "ok": final_verdict == "SUCCESS",
                "verdict": final_verdict,
                "completed_at": now_jst(),
                "elapsed_sec": round(time.monotonic() - state["_started_monotonic"], 1),
                "run_dir": str(run_dir),
                "displacement_kpis": displacement_kpis,
                "displacement_gate_reasons": displacement_reasons,
            }
        )
        return 0 if final_verdict == "SUCCESS" else 1
    except Exception as exc:
        state.update(
            {
                "phase": "error",
                "ok": False,
                "error": str(exc),
                "completed_at": now_jst(),
                "elapsed_sec": round(time.monotonic() - state["_started_monotonic"], 1),
            }
        )
        return 2
    finally:
        stop_event.set()
        write_json(STATUS_PATH, {key: value for key, value in state.items() if not key.startswith("_")})


if __name__ == "__main__":
    raise SystemExit(main())
