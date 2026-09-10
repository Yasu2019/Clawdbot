#!/usr/bin/env python3
"""Compare coarse/refined checkMesh reports without claiming physics convergence."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coarse", type=Path, required=True)
    ap.add_argument("--refined", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    c, f = json.loads(a.coarse.read_text()), json.loads(a.refined.read_text())
    report = {
        "status": "REVIEW",
        "physics_convergence": "NOT_ESTABLISHED",
        "coarse_cells": c.get("cells"), "refined_cells": f.get("cells"),
        "cell_count_ratio": f.get("cells", 0) / max(c.get("cells", 1), 1),
        "total_volume_relative_difference": None,
        "total_volume_comparison": "NOT_COMPARABLE_UNTIL_UNIT_SYSTEM_IS_NORMALIZED",
        "max_non_orthogonality_deg": {"coarse": c.get("max_non_orthogonality_deg"), "refined": f.get("max_non_orthogonality_deg")},
        "max_skewness": {"coarse": c.get("max_skewness"), "refined": f.get("max_skewness")},
        "mesh_quality_gate": c.get("status") == "PASS" and f.get("status") == "PASS",
        "next_step": "run identical Cross-WLF physics on both meshes and compare integral/warpage fields"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
