#!/usr/bin/env python3
"""Generate a gate/vent/viscosity-aware virtual front-arrival field.

This is an explicit screening model, not a replacement for a compressible-air
VOF solve.  It is useful for making weld-line candidates depend on the stated
gate positions, injection speed, vent layout, and virtual viscosity instead of
an arbitrary centre line.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.spatial import cKDTree


def load_points(source: Path):
    obj = pv.read(source)
    grid = obj["internal"] if hasattr(obj, "keys") and "internal" in obj.keys() else obj
    return grid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    g = load_points(args.source.resolve())
    xyz = np.asarray(g.cell_centers().points, dtype=float)
    gates = np.asarray(cfg["gates_mm"], dtype=float) / 1000.0
    vents = np.asarray(cfg["vents_mm"], dtype=float) / 1000.0
    gate_d = np.linalg.norm(xyz[:, None, :] - gates[None, :, :], axis=2)
    gate_id = np.argmin(gate_d, axis=1).astype(np.int16) + 1
    distance = np.min(gate_d, axis=1)
    vent_tree = cKDTree(vents)
    vent_distance, _ = vent_tree.query(xyz, k=1)

    speed = float(cfg["injection_speed_m_s"])
    mu_ref = float(cfg["viscosity_pa_s"])
    ref_speed = float(cfg.get("reference_speed_m_s", 0.02))
    ref_mu = float(cfg.get("reference_viscosity_pa_s", 80.0))
    # Virtual viscosity penalty: higher viscosity reduces the local advance rate.
    viscosity_factor = (mu_ref / ref_mu) ** float(cfg.get("viscosity_exponent", 0.20))
    area = np.asarray(cfg["vent_area_mm2"], dtype=float)
    vent_strength = float(np.sum(area)) / max(float(cfg.get("reference_vent_area_mm2", 12.0)), 1e-12)
    vent_length = float(cfg.get("vent_influence_length_mm", 18.0)) / 1000.0
    # Local vent relief is bounded and decays with distance from the nearest vent.
    relief = float(cfg.get("vent_relief_gain", 0.18)) * vent_strength * np.exp(-vent_distance / vent_length)
    relief = np.clip(relief, 0.0, float(cfg.get("max_vent_relief", 0.35)))
    local_speed = speed / max(viscosity_factor, 1e-9) * (1.0 + relief)
    arrival = distance / np.maximum(local_speed, 1e-9)

    # Geometry-aware front meeting: neighbouring cells must belong to different
    # gate Voronoi regions and have near-equal arrival times.
    _, nn = cKDTree(xyz).query(xyz, k=9, workers=1)
    different = gate_id[nn[:, 1:]] != gate_id[:, None]
    dt = np.abs(arrival[nn[:, 1:]] - arrival[:, None])
    dt = np.where(different, dt, np.inf)
    min_dt = np.min(dt, axis=1)
    tau = float(cfg.get("weld_time_tolerance_s", 0.025))
    weld = np.where(np.isfinite(min_dt), np.exp(-min_dt / tau), 0.0)
    # Hole/edge cells are retained as geometry modifiers, not hard-coded lines.
    weld *= 0.75 + 0.25 * np.clip(np.exp(-vent_distance / vent_length), 0, 1)

    g.cell_data["virtual_arrival_time_s"] = arrival.astype(np.float32)
    g.cell_data["virtual_gate_id"] = gate_id
    g.cell_data["virtual_local_speed_m_s"] = local_speed.astype(np.float32)
    g.cell_data["virtual_viscosity_pa_s"] = np.full(g.n_cells, mu_ref, dtype=np.float32)
    g.cell_data["virtual_vent_relief"] = relief.astype(np.float32)
    g.cell_data["virtual_weld_candidate"] = np.clip(weld, 0, 1).astype(np.float32)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    g.save(args.out.resolve(), binary=True)
    top = np.argsort(weld)[-max(1, g.n_cells // 100):]
    report = {
        "status": "VIRTUAL_FRONT_ARRIVAL_SCREENING",
        "calibration": "MEASURED_DATA_NOT_APPLIED",
        "source": str(args.source.resolve()),
        "output": str(args.out.resolve()),
        "cells": int(g.n_cells),
        "gates_mm": (gates * 1000.0).tolist(),
        "vents_mm": (vents * 1000.0).tolist(),
        "injection_speed_m_s": speed,
        "virtual_viscosity_pa_s": mu_ref,
        "arrival_time_s": {"min": float(arrival.min()), "max": float(arrival.max())},
        "weld_candidate": {
            "criterion": "different-gate neighbours with near-equal arrival time",
            "max": float(weld.max()),
            "top_1pct_centroid_mm": (xyz[top].mean(axis=0) * 1000.0).tolist(),
            "top_1pct_bbox_min_mm": (xyz[top].min(axis=0) * 1000.0).tolist(),
            "top_1pct_bbox_max_mm": (xyz[top].max(axis=0) * 1000.0).tolist(),
        },
        "limitations": ["Virtual viscosity/vent relief law; not measured rheology or vent resistance.",
                        "Candidate location is not weld strength or guaranteed production location."],
    }
    args.out.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
