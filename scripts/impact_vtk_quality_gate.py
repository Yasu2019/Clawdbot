# -*- coding: utf-8 -*-
"""Numeric QC gate for Impact legacy VTK outputs.

This intentionally avoids heavy VTK imports so the gate can run on ThinkPad
before accepting cached PNGs. It rejects clearly nonphysical mesh explosions.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
DISPLACEMENT_FIELDS = {"displacement_magnitude", "displacement", "Displacement"}


def _floats(line: str) -> list[float]:
    out: list[float] = []
    for match in FLOAT_RE.finditer(line):
        try:
            value = float(match.group(0))
        except ValueError:
            continue
        if math.isfinite(value):
            out.append(value)
    return out


def scan_legacy_vtk(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    point_count = 0
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    displacement_max = None
    displacement_name = ""

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        upper = line.upper()
        if upper.startswith("POINTS "):
            parts = line.split()
            point_count = int(parts[1]) if len(parts) >= 2 else 0
            need = point_count * 3
            vals: list[float] = []
            i += 1
            while i < len(lines) and len(vals) < need:
                vals.extend(_floats(lines[i]))
                i += 1
            for p in range(0, min(len(vals), need), 3):
                for axis in range(3):
                    value = vals[p + axis]
                    mins[axis] = min(mins[axis], value)
                    maxs[axis] = max(maxs[axis], value)
            continue
        if upper.startswith("SCALARS "):
            parts = line.split()
            name = parts[1] if len(parts) >= 2 else ""
            collect = name in DISPLACEMENT_FIELDS or name.lower() in {f.lower() for f in DISPLACEMENT_FIELDS}
            vals: list[float] = []
            i += 1
            if i < len(lines) and lines[i].strip().upper().startswith("LOOKUP_TABLE"):
                i += 1
            while i < len(lines):
                probe = lines[i].strip()
                probe_upper = probe.upper()
                if (
                    probe_upper.startswith("SCALARS ")
                    or probe_upper.startswith("VECTORS ")
                    or probe_upper.startswith("FIELD ")
                    or probe_upper.startswith("POINT_DATA ")
                    or probe_upper.startswith("CELL_DATA ")
                ):
                    break
                if collect:
                    vals.extend(_floats(probe))
                i += 1
            if collect and vals:
                displacement_name = name
                displacement_max = max(abs(v) for v in vals if math.isfinite(v))
            continue
        i += 1

    if point_count <= 0 or any(not math.isfinite(v) for v in mins + maxs):
        raise RuntimeError("points_missing_or_invalid")

    spans = [maxs[a] - mins[a] for a in range(3)]
    bbox_diag = math.sqrt(sum(span * span for span in spans))
    coord_abs_max = max(max(abs(v) for v in mins), max(abs(v) for v in maxs))
    return {
        "path": str(path),
        "points": point_count,
        "mins": mins,
        "maxs": maxs,
        "spans": spans,
        "bbox_diag": bbox_diag,
        "coord_abs_max": coord_abs_max,
        "displacement_name": displacement_name,
        "displacement_abs_max": displacement_max,
    }


def evaluate(meta: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    reasons: list[str] = []
    if meta["bbox_diag"] > args.max_bbox_diag:
        reasons.append(f"bbox_diag>{args.max_bbox_diag:g}")
    if meta["coord_abs_max"] > args.max_coordinate_abs:
        reasons.append(f"coord_abs_max>{args.max_coordinate_abs:g}")
    disp = meta.get("displacement_abs_max")
    if disp is not None and disp > args.max_displacement_abs:
        reasons.append(f"displacement_abs_max>{args.max_displacement_abs:g}")
    if meta["points"] < args.min_points:
        reasons.append(f"points<{args.min_points}")
    verdict = "PASS" if not reasons else "FAILED_MESH_EXPLOSION"
    return {"verdict": verdict, "reasons": reasons, "metrics": meta}


def main() -> int:
    parser = argparse.ArgumentParser(description="Impact VTK mesh explosion QC gate")
    parser.add_argument("vtk_path")
    parser.add_argument("--max-bbox-diag", type=float, default=100000.0)
    parser.add_argument("--max-coordinate-abs", type=float, default=100000.0)
    parser.add_argument("--max-displacement-abs", type=float, default=100000.0)
    parser.add_argument("--min-points", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        meta = scan_legacy_vtk(Path(args.vtk_path).resolve())
        result = evaluate(meta, args)
    except Exception as exc:
        result = {"verdict": "FAILED_MESH_EXPLOSION", "reasons": [str(exc)], "metrics": {"path": args.vtk_path}}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        metrics = result.get("metrics") or {}
        print(f"FEM_IMPACT_QC_VERDICT={result['verdict']}")
        print(f"FEM_IMPACT_QC_REASONS={','.join(result.get('reasons') or [])}")
        print(f"FEM_IMPACT_QC_BBOX_DIAG={metrics.get('bbox_diag', '')}")
        print(f"FEM_IMPACT_QC_COORD_ABS_MAX={metrics.get('coord_abs_max', '')}")
        print(f"FEM_IMPACT_QC_DISPLACEMENT_ABS_MAX={metrics.get('displacement_abs_max', '')}")
    return 0 if result["verdict"] == "PASS" else 20


if __name__ == "__main__":
    raise SystemExit(main())
