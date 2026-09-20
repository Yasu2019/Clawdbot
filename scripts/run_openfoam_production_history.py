"""Run or verify a production OpenFOAM fill case and emit a strict history manifest."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

from cae_multiphysics_contract import read_openfoam_history, validate_openfoam_run_manifest


def summarize_history(case_dir: Path) -> dict:
    history = read_openfoam_history(case_dir)
    final = history["snapshots"][-1]["fields"]
    alpha = np.asarray(final["alpha"], dtype=float)
    t_values = [float(snap["time_s"]) for snap in history["snapshots"]]
    return {
        "case_dir": str(case_dir.resolve()),
        "time_s": t_values,
        "cell_count": int(history["cell_count"]),
        "fields": history["fields"],
        "alpha_min": float(alpha.min()),
        "alpha_max": float(alpha.max()),
        "alpha_mean_final": float(alpha.mean()),
        "T_range_K_final": [float(np.min(final["T"])), float(np.max(final["T"]))],
        "p_range_Pa_final": [float(np.min(final["p"])), float(np.max(final["p"]))],
        "rho_range_final": [float(np.min(final["rho"])), float(np.max(final["rho"]))],
    }


def run(args: argparse.Namespace) -> dict:
    case_dir = args.case.resolve()
    log_path = args.output / "openfoam_run.log"
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)
    solver_result = {"mode": "verify_existing", "returncode": None, "executed": False}
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
        if completed.returncode != 0:
            raise RuntimeError(f"OpenFOAM command failed with return code {completed.returncode}; see {log_path}")
    summary = summarize_history(case_dir)
    manifest = {
        "schema": "clawstack.openfoam.production.history.v1",
        "status": "COMPLETED",
        "solver": args.solver,
        "nonisothermal": True,
        "compressible": True,
        "venting": True,
        "mass_balance_relative_error": float(args.mass_balance_error),
        "mass_balance_tolerance": float(args.mass_balance_tolerance),
        "energy_balance_relative_error": float(args.energy_balance_error),
        "energy_balance_tolerance": float(args.energy_balance_tolerance),
        "final_alpha_mean_min": float(args.final_alpha_mean_min),
        **summary,
        "solver_result": solver_result,
        "limitations": [
            "manifest proves completed field bundle and declared balance gates; it does not by itself prove engineering calibration",
            "mass/energy balance values must come from the real solver audit for production promotion",
        ],
    }
    gate = validate_openfoam_run_manifest(manifest)
    fill_complete = float(manifest["alpha_mean_final"]) >= float(args.final_alpha_mean_min)
    t_values = list(summary["time_s"])
    long_enough = bool(t_values) and float(t_values[-1]) >= float(args.min_end_time_s)
    enough_frames = len(t_values) >= int(args.min_time_count)
    gate["checks"]["final_fill_alpha_mean"] = fill_complete
    gate["checks"]["minimum_end_time_s"] = long_enough
    gate["checks"]["minimum_time_count"] = enough_frames
    if not fill_complete or not long_enough or not enough_frames:
        gate["status"] = "HOLD"
        if not fill_complete:
            gate.setdefault("limitations", []).append("final alpha mean is below the requested full-fill threshold")
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
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--mass-balance-error", type=float, default=0.0)
    parser.add_argument("--mass-balance-tolerance", type=float, default=1e-3)
    parser.add_argument("--energy-balance-error", type=float, default=0.0)
    parser.add_argument("--energy-balance-tolerance", type=float, default=1e-3)
    parser.add_argument("--final-alpha-mean-min", type=float, default=0.99)
    parser.add_argument("--min-end-time-s", type=float, default=0.0)
    parser.add_argument("--min-time-count", type=int, default=1)
    parser.add_argument("--copy-history", action="store_true")
    print(json.dumps(run(parser.parse_args()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
