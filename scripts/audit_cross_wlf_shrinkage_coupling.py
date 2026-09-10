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
    viscosity_fields = [p.name for p in final.iterdir()] if final else []
    alpha_bounds = re.findall(r"Min.*?= ([0-9.eE+-]+).*?Max.*?= ([0-9.eE+-]+)", run)
    alpha_ok = bool(alpha_bounds) and all(float(lo) >= -1e-8 and float(hi) <= 1.0000001 for lo, hi in alpha_bounds)
    mass_trace = [float(x) for x in re.findall(r"volIntegrate\(region0\) of rho = ([0-9.eE+-]+)", run)]
    polymer_trace = [float(x) for x in re.findall(r"volIntegrate\(region0\) of alpha\.polymer = ([0-9.eE+-]+)", run)]
    thermal_trace = [float(x) for x in re.findall(r"volIntegrate\(region0\) of T = ([0-9.eE+-]+)", run)]
    dat_path = a.calculix_case / "box_roundhole_shrinkage.dat"
    dat = dat_path.read_text(errors="replace") if dat_path.exists() else ""
    disp_block = re.search(r"displacements .*?\n(.*?)\n\s*stresses", dat, re.S | re.I)
    disp = []
    if disp_block:
        for line in disp_block.group(1).splitlines():
            m = re.match(r"\s*\d+\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
            if m:
                x, y, z = (float(v) for v in m.groups())
                disp.append((x*x + y*y + z*z) ** 0.5)
    stress_block = re.search(r"stresses .*?\n(.*)", dat, re.S | re.I)
    stress_abs = []
    if stress_block:
        for line in stress_block.group(1).splitlines():
            m = re.match(r"\s*\d+\s+\d+\s+(.+)$", line)
            if m:
                try:
                    vals = [float(v) for v in m.group(1).split()]
                except ValueError:
                    continue
                if len(vals) >= 6:
                    stress_abs.extend(abs(v) for v in vals[:6])
    checks = {
        "plugin_compiled": "libcrossWLFViscosityModel.so" in build and "error:" not in build.lower(),
        "plugin_loaded": "Selecting turbulence model type laminar" in run and "crossWLF" in (a.openfoam_case / "constant" / "momentumTransport").read_text(errors="replace"),
        "openfoam_end": re.search(r"\bEnd\s*$", run, re.M) is not None and "FOAM FATAL" not in run,
        "finite_solver_log": "nan" not in run.lower() and "inf" not in run.lower(),
        "finite_state_fields_present": set(("p", "T", "rho", "U")).issubset(fields),
        "viscosity_field_written": any(name.startswith("generalizedNewtonian") for name in viscosity_fields),
        "alpha_bounded": alpha_ok,
        "mass_integral_trace": bool(mass_trace),
        "polymer_volume_trace": bool(polymer_trace),
        "thermal_integral_trace": bool(thermal_trace),
        "calculix_finished": "Job finished" in ccx,
        "calculix_results_present": all((a.calculix_case / f"box_roundhole_shrinkage.{ext}").exists() for ext in ("frd", "dat", "sta")),
        "calculix_displacement_trace": bool(disp),
        "calculix_stress_trace": bool(stress_abs),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
              "openfoam_final_time": final.name if final else None, "openfoam_fields": fields,
              "integrals": {"mass_first": mass_trace[0] if mass_trace else None,
                            "mass_last": mass_trace[-1] if mass_trace else None,
                            "polymer_volume_first": polymer_trace[0] if polymer_trace else None,
                            "polymer_volume_last": polymer_trace[-1] if polymer_trace else None,
                            "thermal_min": min(thermal_trace) if thermal_trace else None,
                            "thermal_max": max(thermal_trace) if thermal_trace else None,
                            "max_displacement": max(disp) if disp else None,
                            "max_abs_stress": max(stress_abs) if stress_abs else None},
              "limitations": ["virtual rheology/CTE/PVT coefficients", "field magnitudes require measured calibration"]}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
