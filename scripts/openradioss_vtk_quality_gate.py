# -*- coding: utf-8 -*-
"""Numeric QC for OpenRadioss legacy VTK before ParaView MP4 / Telegram delivery."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from impact_vtk_quality_gate import (
    evaluate,
    scan_legacy_vtk,
)

# 4mmx4mm ASSY blanking: part span ~10mm; explosion shows bbox >> 80mm
OPENRADIOSS_DEFAULT_LIMITS: dict[str, float | int] = {
    "max_bbox_diag": 80.0,
    "max_coordinate_abs": 60.0,
    "max_displacement_abs": 1e9,
    "min_points": 50,
}


def limits_from_or_cfg(or_cfg: dict[str, Any] | None) -> dict[str, float | int]:
    qc = (or_cfg or {}).get("quality_gate") or {}
    base = dict(OPENRADIOSS_DEFAULT_LIMITS)
    for key in base:
        if qc.get(key) is not None:
            base[key] = type(base[key])(qc[key])
    return base


def limits_from_router_cfg(cfg: dict[str, Any] | None) -> dict[str, float | int]:
    or_cfg = ((cfg or {}).get("tri_track_parallel") or {}).get("openradioss") or {}
    return limits_from_or_cfg(or_cfg)


def latest_vtk(run_dir: Path) -> Path | None:
    run_dir = run_dir.resolve()
    vtks = sorted(run_dir.glob("*.vtk"), key=lambda p: p.name)
    if not vtks:
        vtks = sorted(run_dir.glob("**/*.vtk"), key=lambda p: p.name)
    return vtks[-1] if vtks else None


def qc_vtk_path(vtk_path: Path, limits: dict[str, float | int] | None = None) -> dict[str, Any]:
    lim = limits or dict(OPENRADIOSS_DEFAULT_LIMITS)
    meta = scan_legacy_vtk(vtk_path.resolve())
    ns = argparse.Namespace(
        max_bbox_diag=float(lim["max_bbox_diag"]),
        max_coordinate_abs=float(lim["max_coordinate_abs"]),
        max_displacement_abs=float(lim["max_displacement_abs"]),
        min_points=int(lim["min_points"]),
    )
    return evaluate(meta, ns)


def qc_run_dir(run_dir: Path, limits: dict[str, float | int] | None = None) -> dict[str, Any]:
    vtk = latest_vtk(run_dir)
    if vtk is None:
        return {
            "verdict": "FAILED_MESH_EXPLOSION",
            "reasons": ["vtk_missing"],
            "metrics": {"run_dir": str(run_dir)},
        }
    result = qc_vtk_path(vtk, limits)
    result["metrics"] = dict(result.get("metrics") or {})
    result["metrics"]["qc_vtk"] = str(vtk)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenRadioss VTK mesh explosion QC gate")
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--max-bbox-diag", type=float, default=float(OPENRADIOSS_DEFAULT_LIMITS["max_bbox_diag"]))
    parser.add_argument("--max-coordinate-abs", type=float, default=float(OPENRADIOSS_DEFAULT_LIMITS["max_coordinate_abs"]))
    parser.add_argument("--min-points", type=int, default=int(OPENRADIOSS_DEFAULT_LIMITS["min_points"]))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    limits = {
        "max_bbox_diag": args.max_bbox_diag,
        "max_coordinate_abs": args.max_coordinate_abs,
        "max_displacement_abs": 1e9,
        "min_points": args.min_points,
    }
    result = qc_run_dir(args.run_dir, limits)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"OPENRADIOSS_QC_VERDICT={result.get('verdict')}")
        print(f"OPENRADIOSS_QC_REASONS={','.join(result.get('reasons') or [])}")
        metrics = result.get("metrics") or {}
        if metrics.get("bbox_diag") is not None:
            print(f"OPENRADIOSS_QC_BBOX_DIAG={metrics['bbox_diag']}")
        if metrics.get("coord_abs_max") is not None:
            print(f"OPENRADIOSS_QC_COORD_ABS_MAX={metrics['coord_abs_max']}")
        if metrics.get("qc_vtk"):
            print(f"OPENRADIOSS_QC_VTK={metrics['qc_vtk']}")
    return 0 if result.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
