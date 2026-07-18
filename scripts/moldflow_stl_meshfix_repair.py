# -*- coding: utf-8 -*-
"""Create and validate a MeshFix STL candidate without overwriting the source."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pymeshfix
import trimesh


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def mesh_metrics(mesh: trimesh.Trimesh) -> dict:
    bounds = np.asarray(mesh.bounds, dtype=float)
    extents = np.asarray(mesh.extents, dtype=float)
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "components": int(len(mesh.split(only_watertight=False))),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "bounds_min_mm": bounds[0].tolist(),
        "bounds_max_mm": bounds[1].tolist(),
        "extents_mm": extents.tolist(),
        "area_mm2": float(mesh.area),
        "volume_mm3": float(abs(mesh.volume)),
    }


def relative_extent_drift(before: dict, after: dict) -> list[float]:
    result = []
    for old, new in zip(before["extents_mm"], after["extents_mm"]):
        denominator = max(abs(float(old)), 1.0e-9)
        result.append(abs(float(new) - float(old)) / denominator)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--max-extent-drift", type=float, default=0.005)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    report_path = Path(args.report).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite output: {output}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = source.with_name(f"{source.name}.bak_meshfix_{stamp}")
    shutil.copy2(source, backup)

    original = trimesh.load_mesh(source, force="mesh", process=False)
    if not isinstance(original, trimesh.Trimesh):
        raise TypeError("source did not load as one triangular mesh")
    before = mesh_metrics(original)

    with tempfile.TemporaryDirectory(prefix="moldflow_meshfix_", dir=str(output.parent)) as temp_dir:
        temp_output = Path(temp_dir) / output.name
        fixer = pymeshfix.MeshFix(
            np.asarray(original.vertices, dtype=np.float64),
            np.asarray(original.faces, dtype=np.int32),
            verbose=False,
        )
        fixer.repair(joincomp=True, remove_smallest_components=False)
        repaired = trimesh.Trimesh(
            vertices=np.asarray(fixer.points, dtype=np.float64),
            faces=np.asarray(fixer.faces, dtype=np.int64),
            process=False,
        )
        trimesh.repair.fix_normals(repaired, multibody=True)
        repaired.export(temp_output, file_type="stl")
        shutil.move(str(temp_output), str(output))

    after = mesh_metrics(repaired)
    extent_drift = relative_extent_drift(before, after)
    max_extent_drift = max(extent_drift)
    accepted = (
        after["watertight"]
        and after["winding_consistent"]
        and after["components"] == 1
        and max_extent_drift <= args.max_extent_drift
    )
    report = {
        "status": "PASS" if accepted else "REVIEW",
        "source": str(source),
        "source_sha256": sha256(source),
        "backup": str(backup),
        "backup_sha256": sha256(backup),
        "output": str(output),
        "output_sha256": sha256(output),
        "before": before,
        "after": after,
        "extent_relative_drift": extent_drift,
        "max_extent_relative_drift": max_extent_drift,
        "acceptance": {
            "watertight": after["watertight"],
            "winding_consistent": after["winding_consistent"],
            "single_component": after["components"] == 1,
            "extent_drift_lte": args.max_extent_drift,
        },
        "moldflow_imported": False,
        "analysis_started": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
