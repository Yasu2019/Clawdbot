"""Fail-closed solver entry points for the canonical box-with-round-hole case.

This module deliberately separates execution from engineering acceptance:
OpenFOAM/CalculiX may produce solver artefacts, but no defect or validation
claim is emitted here. Existing output directories are never overwritten.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OF = ROOT / "artifacts" / "box_roundhole_v5" / "fill_l4"
DEFAULT_CCX = ROOT / "artifacts" / "box_roundhole_v5" / "calculix_l1"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_openfoam_case(case: Path) -> dict:
    required = ["system/controlDict", "system/fvSchemes", "system/fvSolution",
                "constant/transportProperties", "0/U", "0/p_rgh", "0/alpha.polymer"]
    missing = [x for x in required if not (case / x).is_file()]
    return {"case": str(case), "required": required, "missing": missing,
            "status": "READY" if not missing else "BLOCKED_MISSING_INPUT"}


def _foam_scalar(path: Path) -> list[float]:
    """Read uniform or nonuniform OpenFOAM scalar fields without claiming units."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"internalField\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(\s*(.*?)\s*\)\s*;", text, re.S)
    if m:
        vals = [float(x) for x in re.findall(r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?", m.group(2))]
        if len(vals) != int(m.group(1)):
            raise ValueError(f"declared {m.group(1)} values, found {len(vals)}: {path}")
        return vals
    m = re.search(r"internalField\s+uniform\s+([-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?)", text)
    if m:
        return [float(m.group(1))]
    raise ValueError(f"unsupported scalar field: {path}")


def map_openfoam_fields(case: Path, out: Path) -> dict:
    """Create an auditable, conservative screening map for a final OpenFOAM time."""
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {out}")
    out.mkdir(parents=True, exist_ok=True)
    fields = {"alpha": case / "2" / "alpha.polymer_0", "pressure": case / "2" / "p_rgh",
              "velocity": case / "2" / "U", "temperature": case / "2" / "T"}
    missing = [k for k, p in fields.items() if k != "velocity" and not p.is_file()]
    result = {"schema": "clawstack.box_roundhole_field_mapping.v1", "case": str(case),
              "target_time": 2.0, "status": "BLOCKED_MISSING_PHYSICS_FIELD" if missing else "SCREENING_MAP_READY",
              "missing": missing, "formal_gate": "HOLD", "engineering_claim": "NONE"}
    if not missing:
        alpha = _foam_scalar(fields["alpha"])
        pressure_pa = _foam_scalar(fields["pressure"])
        result["cell_count"] = {"alpha": len(alpha), "pressure": len(pressure_pa)}
        result["mean_fill_fraction"] = sum(alpha) / len(alpha) if alpha else None
        result["pressure_mpa"] = {"mean": (sum(pressure_pa) / len(pressure_pa) / 1e6) if pressure_pa else None,
                                   "min": min(pressure_pa) / 1e6 if pressure_pa else None,
                                   "max": max(pressure_pa) / 1e6 if pressure_pa else None}
        if len(alpha) != len(pressure_pa):
            result["status"] = "BLOCKED_FIELD_SIZE_MISMATCH"
    (out / "field_mapping.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def prepare_calculix(out: Path, pressure_mpa: float = 8.5, include_thermal: bool = False, estimated_shrinkage: float | None = None) -> dict:
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output: {out}")
    out.mkdir(parents=True, exist_ok=True)
    # Reuse the bounded C3D8 deck generator; its provisional assumptions are
    # recorded and are not promoted to a calibrated warpage result.
    from run_box_of_calculix_mvp import deck

    text, nodes, elements = deck(pressure_mpa)
    # CalculiX's P2 load on every element is fragile for this provisional
    # block deck (internal-face orientation can create a singular response).
    # Use an equivalent, explicitly bounded nodal load on the top surface:
    # pressure [N/mm2] * 100*60 mm2, distributed over nodes 21..40.
    total_force = pressure_mpa * 100.0 * 60.0
    nodal_force = -total_force / 20.0
    text = re.sub(r"\*DLOAD\s+EALL, P2, [^\n]+\n", "*CLOAD\n" + "\n".join(f"{nid}, 3, {nodal_force:.9g}" for nid in range(21, 41)) + "\n", text)
    # Fully support the lower face in the thickness direction and retain only
    # the minimum in-plane references.  The original three-node fixture left
    # in-plane modes coupled to the pressure proxy, producing singular,
    # geometry-scale-exceeding displacements.  Keep this as an explicit
    # screening support assumption; it is not a physical mold constraint.
    def _nset_lines(start: int, stop: int) -> str:
        ids = list(range(start, stop + 1))
        return "\n".join(", ".join(str(n) for n in ids[i:i + 16]) for i in range(0, len(ids), 16))
    text = text.replace("*MATERIAL, NAME=PROVISIONAL_RESIN", "*NSET, NSET=BOTTOM\n" + _nset_lines(1, 20) + "\n*NSET, NSET=TOP\n" + _nset_lines(21, 40) + "\n*MATERIAL, NAME=PROVISIONAL_RESIN")
    text = re.sub(r"\*BOUNDARY\n1, 1, 3\n5, 2, 3\n16, 1, 1", "*BOUNDARY\nBOTTOM, 3, 3\n1, 1, 2\n5, 2, 2\n16, 1, 1", text)
    if estimated_shrinkage is not None:
        # Encode the estimated isotropic linear shrinkage as an explicit
        # eigenstrain proxy over the 30 K screening temperature drop.
        cte_proxy = abs(estimated_shrinkage) / 30.0
        text = re.sub(r"\*EXPANSION\s+0\.00006", f"*EXPANSION\n{cte_proxy:.9g}", text)
    if not include_thermal:
        text = re.sub(r"\*EXPANSION\s+0\.00006\s*\n", "", text)
        text = re.sub(r"\*INITIAL CONDITIONS, TYPE=TEMPERATURE.*?(?=\*CLOAD)", "", text, flags=re.S)
    inp = out / "box_roundhole_screen.inp"
    inp.write_text(text, encoding="utf-8")
    manifest = {
        "schema": "clawstack.box_roundhole_solver.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "solver": "CalculiX",
        "status": "PREPARED_UNVALIDATED_SCREENING",
        "input": inp.name,
        "mesh": {"nodes": nodes, "elements": elements, "type": "C3D8"},
        "pressure_mpa": pressure_mpa,
        "thermal_load": "enabled" if include_thermal else "disabled_for_mechanical_sanity",
        "load_mapping": "top_surface_equivalent_nodal_force",
        "support_mapping": "bottom_face_z_fixed_with_in_plane_reference",
        "estimated_shrinkage_fraction": estimated_shrinkage,
        "engineering_claim": "NONE",
        "required_followup": ["calibrated PVT/CTE/cooling", "field mapping", "mesh convergence", "independent review"],
    }
    _write(out / "solver_manifest.json", manifest)
    return manifest


def mean_pvt_shrinkage(vtu: Path) -> float:
    """Read the virtual/theory PVT shrink field for the structural handoff."""
    import pyvista as pv
    grid = pv.read(vtu)
    if "pvt_shrink_strain" not in grid.cell_data:
        raise ValueError(f"pvt_shrink_strain missing: {vtu}")
    import numpy as np
    values = np.asarray(grid.cell_data["pvt_shrink_strain"], dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError(f"invalid pvt_shrink_strain: {vtu}")
    return float(np.mean(values))


def mean_pressure_mpa(vtu: Path) -> float:
    """Read the calibrated-screening pressure field in MPa."""
    import pyvista as pv
    grid = pv.read(vtu)
    name = "pressure_MPa_calibrated"
    if name not in grid.cell_data:
        raise ValueError(f"{name} missing: {vtu}")
    import numpy as np
    values = np.asarray(grid.cell_data[name], dtype=float)
    if values.size == 0 or not np.isfinite(values).all():
        raise ValueError(f"invalid pressure field: {vtu}")
    return float(np.mean(values))


def run_calculix(out: Path) -> dict:
    out = out.resolve()
    manifest_path = out / "solver_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("prepare-calculix must run first")
    docker = shutil.which("docker")
    if not docker:
        result = {"status": "BLOCKED_DOCKER_MISSING", "returncode": None}
    else:
        run = subprocess.run([docker, "run", "--rm", "--cpus", "2", "--memory", "4g",
                              "-v", f"{out.as_posix()}:/work", "-w", "/work", "calculix/ccx:latest",
                              "ccx", "box_roundhole_screen"], capture_output=True, text=True,
                             timeout=900)
        log = (run.stdout or "") + (run.stderr or "")
        (out / "ccx.log").write_text(log, encoding="utf-8", errors="replace")
        result = {"status": "SOLVER_PASS_UNVALIDATED" if run.returncode == 0 else "SOLVER_FAIL",
                  "returncode": run.returncode, "log": "ccx.log",
                  "dat_present": (out / "box_roundhole_screen.dat").is_file()}
    _write(out / "solver_run.json", result)
    return result


def audit_calculix(out: Path, displacement_limit_mm: float = 120.0) -> dict:
    """Audit CalculiX displacement output for finite, geometry-scale values."""
    dat = out / "box_roundhole_screen.dat"
    result = {"schema": "clawstack.calculix_result_audit.v1", "status": "BLOCKED_NO_DAT",
              "formal_gate": "HOLD", "engineering_claim": "NONE"}
    if dat.is_file():
        text = dat.read_text(encoding="utf-8", errors="replace")
        section = text.split(" stresses ", 1)[0]
        rows = re.findall(r"^\s*\d+\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)\s*$", section, re.M)
        vals = [(float(a), float(b), float(c)) for a, b, c in rows]
        norms = [(a*a + b*b + c*c) ** 0.5 for a, b, c in vals]
        result.update({"nodes": len(vals), "max_displacement_mm": max(norms) if norms else None,
                       "limit_mm": displacement_limit_mm})
        result["status"] = "PASS_NUMERICAL_SANITY_UNVALIDATED" if norms and max(norms) <= displacement_limit_mm else "BLOCKED_NUMERICAL_OUTLIER"
    (out / "result_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate-openfoam")
    v.add_argument("--case", type=Path, default=DEFAULT_OF)
    c = sub.add_parser("prepare-calculix")
    c.add_argument("--out", type=Path, default=DEFAULT_CCX)
    c.add_argument("--pressure-mpa", type=float, default=8.5)
    c.add_argument("--include-thermal", action="store_true")
    c.add_argument("--estimated-shrinkage", type=float, default=None)
    c.add_argument("--shrinkage-vtu", type=Path, default=None,
                   help="Use mean pvt_shrink_strain from a theory-path VTU")
    c.add_argument("--pressure-vtu", type=Path, default=None,
                   help="Use mean pressure_MPa_calibrated from a screening VTU")
    r = sub.add_parser("run-calculix")
    r.add_argument("--out", type=Path, default=DEFAULT_CCX)
    m = sub.add_parser("map-openfoam")
    m.add_argument("--case", type=Path, default=DEFAULT_OF)
    m.add_argument("--out", type=Path, default=ROOT / "artifacts" / "box_roundhole_v5" / "field_mapping_l1")
    a = sub.add_parser("audit-calculix")
    a.add_argument("--out", type=Path, default=DEFAULT_CCX)
    args = p.parse_args()
    if args.command == "validate-openfoam":
        result = validate_openfoam_case(args.case)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "READY" else 2
    if args.command == "prepare-calculix":
        shrink = args.estimated_shrinkage
        pressure = args.pressure_mpa
        source = None
        if args.shrinkage_vtu is not None:
            shrink = mean_pvt_shrinkage(args.shrinkage_vtu)
            source = str(args.shrinkage_vtu.resolve())
        if args.pressure_vtu is not None:
            pressure = mean_pressure_mpa(args.pressure_vtu)
        result = prepare_calculix(args.out, pressure, args.include_thermal, shrink)
        if source:
            result["shrinkage_source_vtu"] = source
        if args.pressure_vtu is not None:
            result["pressure_source_vtu"] = str(args.pressure_vtu.resolve())
        if source or args.pressure_vtu is not None:
            _write(args.out / "solver_manifest.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "map-openfoam":
        result = map_openfoam_fields(args.case, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "SCREENING_MAP_READY" else 2
    if args.command == "audit-calculix":
        result = audit_calculix(args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS_NUMERICAL_SANITY_UNVALIDATED" else 2
    result = run_calculix(args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SOLVER_PASS_UNVALIDATED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
