#!/usr/bin/env python3
"""Audit the OpenFOAM custom transport run and CalculiX reanalysis outputs."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--openfoam-case", type=Path, required=True)
    ap.add_argument("--calculix-case", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    build = (a.openfoam_case / "plugin_build.log").read_text(errors="replace") if (a.openfoam_case / "plugin_build.log").exists() else ""
    run = (a.openfoam_case / "solver.log").read_text(errors="replace") if (a.openfoam_case / "solver.log").exists() else ""
    ccx = (a.calculix_case / "ccx.log").read_text(errors="replace") if (a.calculix_case / "ccx.log").exists() else ""
    times = [p for p in a.openfoam_case.iterdir() if p.is_dir() and re.fullmatch(r"\d+(?:\.\d+)?", p.name)]
    final = max(times, key=lambda p: float(p.name)) if times else None
    fields = [x for x in ("p", "p_rgh", "T", "rho", "U") if final and (final / x).exists()]
    checks = {
        "plugin_compiled": "libcrossWLFViscosityModel.so" in build and "error:" not in build.lower(),
        "plugin_loaded": "Selecting turbulence model type laminar" in run and "crossWLF" in (a.openfoam_case / "constant" / "momentumTransport").read_text(errors="replace"),
        "openfoam_end": re.search(r"\bEnd\s*$", run, re.M) is not None and "FOAM FATAL" not in run,
        "finite_state_fields_present": set(("p", "T", "rho", "U")).issubset(fields),
        "calculix_finished": "Job finished" in ccx,
        "calculix_results_present": all((a.calculix_case / f"box_roundhole_shrinkage.{ext}").exists() for ext in ("frd", "dat", "sta")),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
              "openfoam_final_time": final.name if final else None, "openfoam_fields": fields,
              "limitations": ["virtual rheology/CTE/PVT coefficients", "field magnitudes require measured calibration"]}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
