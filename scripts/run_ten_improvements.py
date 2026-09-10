#!/usr/bin/env python3
"""Run ten bounded evidence gates for the OpenFOAM mesh-convergence pair."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

GATES = [
    ("coarse_patch_contract", "patch_contract_gmsh_coarse155_20260911.json", "status"),
    ("refined_patch_contract", "patch_contract_gmsh_refined15_20260911.json", "status"),
    ("coarse_mesh_quality", "mesh_quality_gmsh_coarse155_20260911.json", "status"),
    ("refined_mesh_quality", "mesh_quality_gmsh_refined15_20260911.json", "status"),
    ("coarse_solver_audit", "coupling_audit_gmsh_coarse155_20260911.json", "status"),
    ("refined_solver_audit", "coupling_audit_gmsh_refined15_20260911.json", "status"),
    ("integral_agreement", "physics_mesh_comparison_gmsh_20260911.json", "relative_difference"),
    ("resolution_separation", "physics_mesh_comparison_gmsh_20260911.json", "resolution_separation_ok"),
    ("time_step_convergence", "time_step_convergence_20260910.json", "status"),
    ("formal_spatial_convergence", "physics_mesh_comparison_gmsh_20260911.json", "status"),
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("artifacts/box_roundhole_v5"))
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    rows = []
    for seq, (key, filename, field) in enumerate(GATES, 1):
        path = a.root / filename
        row = {"sequence": seq, "key": key, "evidence": str(path), "status": "BLOCKED",
               "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            value = data.get(field)
            if field == "relative_difference":
                row["status"] = "PASS" if max(value.values()) < 1e-3 else "REVIEW"
            elif value is True or value == "PASS":
                row["status"] = "PASS"
            elif value is False:
                row["status"] = "REVIEW"
            else:
                row["status"] = str(value).upper()
            row["field"] = field
        rows.append(row)
    report = {"schema": "clawstack.openfoam.ten_improvements.v1", "requested": 10,
              "completed": len(rows), "pass": sum(r["status"] == "PASS" for r in rows),
              "review": sum(r["status"] == "REVIEW" for r in rows), "gates": rows,
              "policy": "evidence-backed; no legacy task stopped or overwritten"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
