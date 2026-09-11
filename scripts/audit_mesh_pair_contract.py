#!/usr/bin/env python3
"""Audit a coarse/refined mesh pair before allowing a convergence claim."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coarse", type=Path, required=True)
    ap.add_argument("--refined", type=Path, required=True)
    ap.add_argument("--coarse-contract", type=Path, required=True)
    ap.add_argument("--refined-contract", type=Path, required=True)
    ap.add_argument("--coarse-mesh", type=Path, required=True)
    ap.add_argument("--refined-mesh", type=Path, required=True)
    ap.add_argument("--min-ratio", type=float, default=1.10)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    cm, rm = read(a.coarse_mesh), read(a.refined_mesh)
    cc, rc = read(a.coarse_contract), read(a.refined_contract)
    coarse_cells, refined_cells = float(cm["cells"]), float(rm["cells"])
    ratio = max(coarse_cells, refined_cells) / min(coarse_cells, refined_cells)
    checks = {
        "coarse_patch_contract": cc.get("status") == "PASS",
        "refined_patch_contract": rc.get("status") == "PASS",
        "coarse_mesh_quality": cm.get("status") == "PASS",
        "refined_mesh_quality": rm.get("status") == "PASS",
        "distinct_cell_count": coarse_cells != refined_cells,
        "minimum_resolution_ratio": ratio >= a.min_ratio,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "REVIEW",
        "checks": checks,
        "coarse_cells": coarse_cells,
        "refined_cells": refined_cells,
        "cell_ratio": ratio,
        "minimum_ratio": a.min_ratio,
        "note": "A pair with insufficient resolution separation is not a formal convergence study.",
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
