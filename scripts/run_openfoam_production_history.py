"""Run or verify an OpenFOAM fill case and emit fail-closed evidence.

An existing time directory is not proof that a solver completed.  Promotion
therefore requires a completed solver log, a multi-frame raw history, mesh and
history fingerprints, full-fill metrics, and a solver-derived balance audit.
"""
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
import subprocess
from pathlib import Path

import numpy as np

from cae_multiphysics_contract import read_openfoam_history, validate_openfoam_run_manifest


FATAL_LOG_MARKERS = (
    "FOAM FATAL ERROR",
    "Floating point exception",
    "SIGFPE",
    "Segmentation fault",
    "Negative initial temperature",
)

ACCEPTED_BALANCE_AUDIT_SOURCES = {
    "solver_function_object",
    "postprocess_integral",
}


def _digest_mapping(values: dict[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def mesh_fingerprint(case_dir: Path) -> tuple[str | None, list[str]]:
    mesh_dir = case_dir / "constant" / "polyMesh"
    files = sorted(path for path in mesh_dir.glob("*") if path.is_file()) if mesh_dir.is_dir() else []
    digests = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    return (_digest_mapping(digests), sorted(digests)) if digests else (None, [])


def inspect_solver_log(path: Path | None, *, returncode: int | None, executed: bool) -> dict:
    if path is None or not path.is_file():
        return {
            "path": str(path) if path else None,
            "executed_by_runner": executed,
            "returncode": returncode,
            "end_marker": False,
            "fatal_markers": [],
            "completed": False,
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    fatal = [marker for marker in FATAL_LOG_MARKERS if marker.lower() in text.lower()]
    end_marker = any(line.strip() == "End" for line in text.splitlines())
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "executed_by_runner": executed,
        "returncode": returncode,
        "end_marker": end_marker,
        "fatal_markers": fatal,
        "completed": end_marker and not fatal and (returncode in (None, 0)),
    }


def load_balance_audit(path: Path | None, args: argparse.Namespace) -> dict:
    if path is not None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("balance audit must be a JSON object")
        return {
            "source": payload.get("source", "unknown"),
            "source_path": str(path.resolve()),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mass_balance_relative_error": float(payload["mass_balance_relative_error"]),
            "energy_balance_relative_error": float(payload["energy_balance_relative_error"]),
        }
    return {
        "source": "declared_cli_unverified",
        "source_path": None,
        "mass_balance_relative_error": float(getattr(args, "mass_balance_error", 0.0)),
        "energy_balance_relative_error": float(getattr(args, "energy_balance_error", 0.0)),
    }


def summarize_history(case_dir: Path) -> dict:
    history = read_openfoam_history(case_dir)
    final = history["snapshots"][-1]["fields"]
    alpha = np.asarray(final["alpha"], dtype=float)
    t_values = [float(snap["time_s"]) for snap in history["snapshots"]]
    filled_cell_alpha_min = 0.99
    return {
        "case_dir": str(case_dir.resolve()),
        "time_s": t_values,
        "cell_count": int(history["cell_count"]),
        "fields": history["fields"],
        "alpha_min": float(alpha.min()),
        "alpha_max": float(alpha.max()),
        "alpha_mean_final": float(alpha.mean()),
        "filled_cell_alpha_min": filled_cell_alpha_min,
        "filled_cell_fraction_final": float(np.mean(alpha >= filled_cell_alpha_min)),
        "T_range_K_final": [float(np.min(final["T"])), float(np.max(final["T"]))],
        "p_range_Pa_final": [float(np.min(final["p"])), float(np.max(final["p"]))],
        "rho_range_final": [float(np.min(final["rho"])), float(np.max(final["rho"]))],
        "history_time_count": len(t_values),
        "history_fingerprint_sha256": _digest_mapping(history["source_sha256"]),
        "history_source_sha256": history["source_sha256"],
    }


def run(args: argparse.Namespace) -> dict:
    case_dir = args.case.resolve()
    log_path = args.output / "openfoam_run.log"
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    solver_result = {"mode": "verify_existing", "returncode": None, "executed": False}
    evidence_log = Path(args.solver_log).resolve() if getattr(args, "solver_log", None) else None
    if args.execute:
        command = args.command or ("Allrun" if (case_dir / "Allrun").exists() else "")
        if not command:
            raise ValueError("--execute requires --command or an Allrun file in the case")
        shell_cmd = command if isinstance(command, str) else " ".join(command)
        completed = subprocess.run(
            shell_cmd,
            cwd=case_dir,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout,
        )
        log_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
        solver_result = {"mode": "execute", "command": shell_cmd, "returncode": completed.returncode, "executed": True, "log": str(log_path)}
        evidence_log = log_path
        if completed.returncode != 0:
            raise RuntimeError(f"OpenFOAM command failed with return code {completed.returncode}; see {log_path}")
    summary = summarize_history(case_dir)
    mesh_sha256, mesh_files = mesh_fingerprint(case_dir)
    solver_evidence = inspect_solver_log(
        evidence_log,
        returncode=solver_result["returncode"],
        executed=solver_result["executed"],
    )
    balance_audit = load_balance_audit(
        Path(args.audit_json).resolve() if getattr(args, "audit_json", None) else None,
        args,
    )
    filled_cell_alpha_min = float(getattr(args, "filled_cell_alpha_min", 0.99))
    final_alpha = np.asarray(read_openfoam_history(case_dir)["snapshots"][-1]["fields"]["alpha"], dtype=float)
    summary["filled_cell_alpha_min"] = filled_cell_alpha_min
    summary["filled_cell_fraction_final"] = float(np.mean(final_alpha >= filled_cell_alpha_min))
    manifest = {
        "schema": "clawstack.openfoam.production.history.v1",
        "status": "COMPLETED",
        "solver": args.solver,
        "nonisothermal": True,
        "compressible": True,
        "venting": True,
        "source_kind": "raw_openfoam_solver_history",
        "synthetic": False,
        "proxy": False,
        "mass_balance_relative_error": balance_audit["mass_balance_relative_error"],
        "mass_balance_tolerance": float(args.mass_balance_tolerance),
        "energy_balance_relative_error": balance_audit["energy_balance_relative_error"],
        "energy_balance_tolerance": float(args.energy_balance_tolerance),
        "final_alpha_mean_min": float(args.final_alpha_mean_min),
        "filled_cell_fraction_min": float(getattr(args, "filled_cell_fraction_min", 0.99)),
        **summary,
        "solver_result": solver_result,
        "solver_execution_evidence": solver_evidence,
        "balance_audit": balance_audit,
        "mesh_fingerprint_sha256": mesh_sha256,
        "mesh_fingerprint_files": mesh_files,
        "limitations": [
            "manifest proves completed field bundle and declared balance gates; it does not by itself prove engineering calibration",
            "mass/energy balance values must come from the real solver audit for production promotion",
        ],
    }
    gate = validate_openfoam_run_manifest(manifest)
    fill_complete = float(manifest["alpha_mean_final"]) >= float(args.final_alpha_mean_min)
    filled_cells_complete = float(manifest["filled_cell_fraction_final"]) >= float(
        getattr(args, "filled_cell_fraction_min", 0.99)
    )
    t_values = list(summary["time_s"])
    long_enough = bool(t_values) and float(t_values[-1]) >= float(args.min_end_time_s)
    enough_frames = len(t_values) >= int(args.min_time_count)
    gate["checks"]["final_fill_alpha_mean"] = fill_complete
    gate["checks"]["filled_cell_fraction"] = filled_cells_complete
    gate["checks"]["minimum_end_time_s"] = long_enough
    gate["checks"]["minimum_time_count"] = enough_frames
    if not fill_complete or not filled_cells_complete or not long_enough or not enough_frames:
        gate["status"] = "HOLD"
        if not fill_complete:
            gate.setdefault("limitations", []).append("final alpha mean is below the requested full-fill threshold")
        if not filled_cells_complete:
            gate.setdefault("limitations", []).append("filled-cell fraction is below the requested full-fill threshold")
        if not long_enough:
            gate.setdefault("limitations", []).append("history end time is below the requested long-run threshold")
        if not enough_frames:
            gate.setdefault("limitations", []).append("history has fewer complete field snapshots than requested")
    manifest["run_gate"] = gate
    manifest["status"] = "COMPLETED" if gate["status"] == "PASS" else "HOLD"
    out_manifest = args.output / "openfoam_production_history_manifest.json"
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.copy_history:
        target = args.output / "history"
        shutil.copytree(case_dir, target, ignore=shutil.ignore_patterns("processor*", "log.*"))
        manifest["copied_history"] = str(target)
        out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solver", default="compressibleInterFoam/custom")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--command")
    parser.add_argument("--solver-log", type=Path, help="Completed raw solver log for verify-existing mode")
    parser.add_argument("--audit-json", type=Path, help="Solver-derived mass/energy balance audit")
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--mass-balance-error", type=float, default=0.0)
    parser.add_argument("--mass-balance-tolerance", type=float, default=1e-3)
    parser.add_argument("--energy-balance-error", type=float, default=0.0)
    parser.add_argument("--energy-balance-tolerance", type=float, default=1e-3)
    parser.add_argument("--final-alpha-mean-min", type=float, default=0.99)
    parser.add_argument("--filled-cell-alpha-min", type=float, default=0.99)
    parser.add_argument("--filled-cell-fraction-min", type=float, default=0.99)
    parser.add_argument("--min-end-time-s", type=float, default=0.0)
    parser.add_argument("--min-time-count", type=int, default=2)
    parser.add_argument("--copy-history", action="store_true")
    report = run(parser.parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
