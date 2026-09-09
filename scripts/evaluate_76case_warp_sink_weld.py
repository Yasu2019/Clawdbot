#!/usr/bin/env python3
"""Screen 76Case warp, sink and weld risks from calibrated fill results.

Outputs are dimensionless engineering-screening indices, not validated
deflection, sink depth, or weld strength predictions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.spatial import cKDTree


def normalize(x: np.ndarray, lo: float = 5, hi: float = 95) -> np.ndarray:
    a, b = np.percentile(x, [lo, hi])
    return np.clip((x - a) / max(float(b - a), 1e-12), 0.0, 1.0)


def top_location(centers_mm: np.ndarray, risk: np.ndarray) -> dict:
    imax = int(np.argmax(risk))
    threshold = float(np.percentile(risk, 99.0))
    selected = centers_mm[risk >= threshold]
    return {
        "max_risk": float(risk[imax]),
        "max_cell_center_mm": centers_mm[imax].tolist(),
        "top_1pct_centroid_mm": selected.mean(axis=0).tolist(),
        "top_1pct_bbox_min_mm": selected.min(axis=0).tolist(),
        "top_1pct_bbox_max_mm": selected.max(axis=0).tolist(),
        "top_1pct_cells": int(len(selected)),
    }


def render(grid: pv.UnstructuredGrid, field: str, target: Path, title: str) -> None:
    p = pv.Plotter(off_screen=True, window_size=(1400, 800))
    p.set_background("white")
    p.add_mesh(grid.extract_surface(), scalars=field, cmap="turbo", clim=(0, 1),
               scalar_bar_args={"title": "Relative risk 0-1"})
    p.view_xy()
    p.camera.roll = 90
    p.camera.zoom(1.15)
    p.add_text(title, color="black", font_size=18)
    p.screenshot(target)
    p.close()


def evaluate(source: Path, out: Path, case: str) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    grid = pv.read(source)
    centers = np.asarray(grid.cell_centers().points, dtype=np.float64)
    centers_mm = centers * 1000.0
    arrival = np.asarray(grid.cell_data["arrival_time_s"], dtype=np.float64)
    temperature = np.asarray(grid.cell_data["temperature_C_proxy"], dtype=np.float64)
    pressure = np.asarray(grid.cell_data["pressure_MPa_calibrated"], dtype=np.float64)
    gate = np.asarray(grid.cell_data["gate_id"], dtype=np.int16)
    region = np.asarray(grid.cell_data.get("surface_region_id", np.zeros(grid.n_cells)), dtype=np.float64)

    # Approximate local half-thickness as distance from a volume-cell centre to
    # the closest surface-cell centre. It is a ranking proxy only.
    surface_centers = np.asarray(grid.extract_surface().cell_centers().points)
    half_thickness = cKDTree(surface_centers).query(centers, k=1, workers=1)[0]

    # Neighbourhood variation indicates differential thermal/flow history,
    # which drives differential shrinkage and therefore warpage tendency.
    _, nn = cKDTree(centers).query(centers, k=9, workers=1)
    temp_spread = np.std(temperature[nn[:, 1:]], axis=1)
    arrival_spread = np.std(arrival[nn[:, 1:]], axis=1)
    # Explicit geometry descriptors.  These supplement the neighbourhood
    # terms so shape is not represented only implicitly by cell connectivity.
    x, y, _ = centers.T
    edge_x = np.minimum(x - x.min(), x.max() - x)
    edge_y = np.minimum(y - y.min(), y.max() - y)
    corner_factor = np.exp(-edge_x / 0.003) * np.exp(-edge_y / 0.003)
    hole_factor = (region == 7).astype(float)
    thickness_gradient = np.std(half_thickness[nn[:, 1:]], axis=1)
    geometry_factor = np.clip(0.45 * corner_factor + 0.30 * hole_factor +
                              0.25 * normalize(thickness_gradient), 0, 1)
    warp = (0.50 * normalize(temp_spread) + 0.28 * normalize(arrival_spread) +
            0.12 * normalize(arrival) + 0.10 * geometry_factor)

    # Thick, late and relatively low-pressure zones receive high sink risk.
    sink = (0.40 * normalize(half_thickness) + 0.25 * normalize(thickness_gradient) +
            0.20 * normalize(arrival) + 0.15 * (1.0 - normalize(pressure)))

    # A weld candidate requires neighbouring cells won by different gates.
    # Rank candidates by similar front-arrival time and relatively low local
    # temperature. Avoid the legacy absolute 150 C cutoff, which collapses to
    # zero for this fast cooling proxy.
    neighbour_gate = gate[nn[:, 1:]]
    different = neighbour_gate != gate[:, None]
    neighbour_dt = np.abs(arrival[nn[:, 1:]] - arrival[:, None])
    different_dt = np.where(different, neighbour_dt, np.inf)
    min_different_dt = np.min(different_dt, axis=1)
    boundary = np.isfinite(min_different_dt)
    arrival_match = np.zeros(grid.n_cells, dtype=float)
    arrival_match[boundary] = np.exp(-min_different_dt[boundary] / 0.025)
    relative_cold = 0.30 + 0.70 * (1.0 - normalize(temperature))
    # Shape modifies how strongly a front-interference candidate is retained;
    # the different-gate neighbour test remains mandatory.
    weld = boundary.astype(float) * arrival_match * relative_cold * (0.75 + 0.25 * geometry_factor)

    warp = np.clip(warp, 0, 1).astype(np.float32)
    sink = np.clip(sink, 0, 1).astype(np.float32)
    weld = np.clip(weld, 0, 1).astype(np.float32)
    grid.cell_data["warpage_risk_proxy"] = warp
    grid.cell_data["sink_risk_proxy"] = sink
    grid.cell_data["weld_risk_proxy"] = weld
    grid.cell_data["half_thickness_m_proxy"] = half_thickness.astype(np.float32)
    grid.cell_data["geometry_shape_factor_proxy"] = geometry_factor.astype(np.float32)
    grid.cell_data["corner_shape_factor_proxy"] = np.clip(corner_factor, 0, 1).astype(np.float32)
    grid.cell_data["hole_shape_factor_proxy"] = hole_factor.astype(np.float32)
    result = out / f"{case}_quality_screening.vtu"
    grid.save(result, binary=True)

    metrics = {}
    for name, values in (("warpage", warp), ("sink", sink), ("weld", weld)):
        metrics[name] = {
            "mean": float(np.mean(values)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
            "fraction_over_0_7": float(np.mean(values >= 0.7)),
            "location": top_location(centers_mm, values),
        }
        render(grid, f"{name}_risk_proxy" if name != "warpage" else "warpage_risk_proxy",
               out / f"{case}_{name}_risk.png", f"{case} {name} relative-risk screening")

    summary = {
        "schema": "76case.quality-screening.v1",
        "case": case,
        "source": str(source),
        "cells": int(grid.n_cells),
        "metrics": metrics,
        "interpretation": {
            "warpage": "relative differential cooling/flow-history risk; not deflection mm",
            "sink": "relative thick/late/low-pressure risk; not sink depth mm",
            "weld": "relative different-gate front-interference risk; not weld strength",
            "shape": "explicit corner/hole/thickness-transition proxies are included; not a CAD/vent-network solve",
        },
        "limitations": [
            "No pack/hold, PVT shrinkage, ejection or structural deformation solve.",
            "Half-thickness is a nearest-surface-centre proxy.",
            "Cooling and viscosity fields inherit the existing proxy models.",
        ],
        "result_vtu": str(result),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path)
    ap.add_argument("--case", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    print(json.dumps(evaluate(args.source.resolve(), args.out.resolve(), args.case), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
