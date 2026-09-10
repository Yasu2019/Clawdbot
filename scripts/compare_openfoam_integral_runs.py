#!/usr/bin/env python3
"""Compare OpenFOAM integral audits with explicit volume unit scaling."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coarse", type=Path, required=True)
    ap.add_argument("--refined", type=Path, required=True)
    ap.add_argument("--coarse-volume-scale", type=float, default=1.0)
    ap.add_argument("--coarse-contract", type=Path, help="patch-contract JSON for the coarse run")
    ap.add_argument("--refined-contract", type=Path, help="patch-contract JSON for the refined run")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    c = json.loads(a.coarse.read_text())["integrals"]
    f = json.loads(a.refined.read_text())["integrals"]
    names = ("mass_last", "polymer_volume_last", "thermal_max")
    rel = {}
    for name in names:
        cv = c[name] * a.coarse_volume_scale
        fv = f[name]
        rel[name] = abs(cv - fv) / max(abs(fv), 1e-30)
    contract_status = {}
    for label, path in (("coarse", a.coarse_contract), ("refined", a.refined_contract)):
        if path is not None:
            contract_status[label] = json.loads(path.read_text(encoding="utf-8")).get("status", "MISSING")
    contract_ok = all(v == "PASS" for v in contract_status.values()) if contract_status else True
    numerical_ok = max(rel.values()) < 1e-3
    report = {
        "status": "PASS" if numerical_ok and contract_ok else ("BLOCKED" if not contract_ok else "REVIEW"),
        "physics_convergence": "SCREENING_PASS" if numerical_ok and contract_ok else "NOT_ESTABLISHED",
        "coarse_volume_scale": a.coarse_volume_scale,
        "coarse_scaled": {n: c[n] * a.coarse_volume_scale for n in names},
        "refined": {n: f[n] for n in names},
        "relative_difference": rel,
        "criterion": "max relative difference < 1e-3",
        "patch_contract_status": contract_status,
        "patch_contract_required": bool(contract_status),
        "note": "Both runs must use identical SI geometry, injection schedule, BCs and material coefficients before this is a formal mesh-convergence result."}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
