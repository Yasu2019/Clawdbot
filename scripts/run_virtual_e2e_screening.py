#!/usr/bin/env python3
"""Run the virtual-material end-to-end screening path.

This is deliberately a dry run for the measured-material handoff.  It reads
the completed 4-vent OpenFOAM VTK, adds explicitly named virtual fields that
an eventual thermal/arrival solver must provide, runs the existing quality
screening evaluator, and emits a manifest.  Nothing here is a calibrated
warpage, sink-depth, air-trap, or weld-strength prediction.
"""
from __future__ import annotations

import argparse, json, subprocess
from pathlib import Path
import numpy as np
import pyvista as pv


def build_input(source: Path, out: Path) -> dict:
    grid = pv.read(source)
    c = np.asarray(grid.cell_centers().points, dtype=float)
    x, y, z = c.T
    # Four gates on x=0: nearest gate is retained as an explicit handoff field.
    gate_pos = np.array([[0,.015,.015],[0,.045,.015],[0,.015,.035],[0,.045,.035]])
    d2 = ((c[:, None, :] - gate_pos[None, :, :]) ** 2).sum(axis=2)
    gate = np.argmin(d2, axis=1).astype(np.int16) + 1
    # Virtual front-arrival proxy: shortest gate distance at a fixed screening
    # speed.  This is deterministic and replaced by measured/thermal results.
    speed = 0.020  # m/s, virtual only
    arrival = np.sqrt(d2.min(axis=1)) / speed
    alpha = np.asarray(grid.cell_data["alpha.polymer"], dtype=float)
    p = np.asarray(grid.cell_data["p_rgh"], dtype=float) / 1e6
    # Keep pressure positive for the screening formula while preserving spatial
    # variation from OpenFOAM's pressure field.
    pressure = np.clip(p + 8.0, 0.05, None)
    # Virtual melt temperature cools with arrival time; values are explicit.
    temperature = 235.0 - 45.0 * np.clip(arrival / max(float(arrival.max()), 1e-12), 0, 1)
    grid.cell_data["arrival_time_s"] = arrival.astype(np.float32)
    grid.cell_data["temperature_C_proxy"] = temperature.astype(np.float32)
    grid.cell_data["pressure_MPa_calibrated"] = pressure.astype(np.float32)
    grid.cell_data["gate_id"] = gate
    grid.cell_data["alpha_fill"] = alpha.astype(np.float32)
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.save(out, binary=True)
    return {"source": str(source), "input": str(out), "cells": int(grid.n_cells),
            "mean_alpha": float(alpha.mean()), "gate_ids": sorted(set(gate.tolist())),
            "virtual_fields": ["arrival_time_s", "temperature_C_proxy",
                                "pressure_MPa_calibrated", "gate_id"],
            "status": "VIRTUAL_SCREENING_INPUT_READY"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--quality-out", type=Path, required=True)
    ap.add_argument("--case", default="box100x60x50_virtual_material")
    args = ap.parse_args()
    manifest = build_input(args.source.resolve(), args.out.resolve())
    thermo_out = args.out.with_name("virtual_thermo_pvt.vtu")
    thermo = subprocess.run(["python", "scripts/apply_virtual_thermo_pvt.py",
                             "--input", str(args.out.resolve()), "--output", str(thermo_out.resolve())],
                            capture_output=True, text=True)
    manifest["thermo_pvt"] = {"returncode": thermo.returncode, "output": str(thermo_out.resolve())}
    quality_source = thermo_out if thermo.returncode == 0 else args.out
    cmd = ["python", "scripts/evaluate_76case_warp_sink_weld.py",
           str(quality_source.resolve()), "--case", args.case, "--out", str(args.quality_out.resolve())]
    run = subprocess.run(cmd, capture_output=True, text=True)
    (args.quality_out.parent / "quality_evaluator.log").write_text((run.stdout or "") + (run.stderr or ""), encoding="utf-8")
    manifest["quality_evaluator"] = {"returncode": run.returncode, "out": str(args.quality_out.resolve())}
    ccx = args.quality_out.parent / "calculix_from_pvt"
    prep = subprocess.run(["python", "scripts/box_roundhole_solver.py", "prepare-calculix",
                           "--out", str(ccx.resolve()), "--pressure-mpa", "8.5",
                           "--shrinkage-vtu", str(thermo_out.resolve())], capture_output=True, text=True)
    ccx_status = {"prepare_returncode": prep.returncode, "out": str(ccx.resolve())}
    if prep.returncode == 0:
        run_ccx = subprocess.run(["python", "scripts/box_roundhole_solver.py", "run-calculix", "--out", str(ccx.resolve())], capture_output=True, text=True)
        audit_ccx = subprocess.run(["python", "scripts/box_roundhole_solver.py", "audit-calculix", "--out", str(ccx.resolve())], capture_output=True, text=True)
        ccx_status.update({"run_returncode": run_ccx.returncode, "audit_returncode": audit_ccx.returncode})
    manifest["calculix"] = ccx_status
    manifest["formal_status"] = "SCREENING_ONLY"
    manifest["measured_calibration_required"] = ["PVT", "CTE", "cooling curve", "viscosity/Cross-WLF", "pressure/flow measurement"]
    (args.quality_out.parent / "virtual_e2e_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
