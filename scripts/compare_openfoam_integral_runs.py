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
    report = {
        "status": "REVIEW" if max(rel.values()) >= 1e-3 else "PASS",
        "physics_convergence": "NOT_ESTABLISHED" if max(rel.values()) >= 1e-3 else "SCREENING_PASS",
        "coarse_volume_scale": a.coarse_volume_scale,
        "coarse_scaled": {n: c[n] * a.coarse_volume_scale for n in names},
        "refined": {n: f[n] for n in names},
        "relative_difference": rel,
        "criterion": "max relative difference < 1e-3",
        "note": "Both runs must use identical SI geometry, injection schedule, BCs and material coefficients before this is a formal mesh-convergence result."}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
