#!/usr/bin/env python3
"""Run a bounded, auditable improvement chain without mutating legacy cases."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

STEPS = [
    ("patch_contract", "validate gate/vent patch areas and normals"),
    ("mesh_quality", "check cells, volumes, non-orthogonality and skewness"),
    ("cross_wlf_load", "confirm custom Cross-WLF model is selected"),
    ("viscosity_output", "confirm generalizedNewtonian viscosity field is written"),
    ("alpha_bounds", "confirm VOF alpha remains bounded"),
    ("mass_integral", "record rho volume integral"),
    ("polymer_volume_integral", "record polymer volume integral"),
    ("thermal_integral", "record temperature volume integral"),
    ("time_step_convergence", "compare half-step integral results"),
    ("calculix_displacement", "extract maximum displacement"),
    ("calculix_stress", "extract maximum stress"),
    ("spatial_convergence", "compare feature-preserving coarse/refined runs"),
]

EVIDENCE = {
    "patch_contract": ("artifacts/box_roundhole_v5/patch_contract_feature_preserving_coarse_20260910.json", "status"),
    "mesh_quality": ("artifacts/box_roundhole_v5/mesh_quality_20260910.json", "status"),
    "cross_wlf_load": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.plugin_loaded"),
    "viscosity_output": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.viscosity_field_written"),
    "alpha_bounds": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.alpha_bounded"),
    "mass_integral": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.mass_integral_trace"),
    "polymer_volume_integral": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.polymer_volume_trace"),
    "thermal_integral": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.thermal_integral_trace"),
    "time_step_convergence": ("artifacts/box_roundhole_v5/time_step_convergence_20260910.json", "status"),
    "calculix_displacement": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.calculix_displacement_trace"),
    "calculix_stress": ("artifacts/box_roundhole_v5/coupling_audit_20260910.json", "checks.calculix_stress_trace"),
    "spatial_convergence": ("artifacts/box_roundhole_v5/physics_mesh_comparison_si_20260910.json", "status"),
}

def lookup(obj, path):
    for part in path.split("."):
        obj = obj[part]
    return obj

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--count", type=int, default=12)
    ap.add_argument("--status", type=str, default=None, help="override status only for an explicit dry-run")
    args = ap.parse_args()
    ledger = []
    for i in range(args.start, min(args.start + args.count, 51)):
        key, description = STEPS[(i - 1) % len(STEPS)]
        evidence_file, evidence_key = EVIDENCE[key]
        evidence_path = Path(evidence_file)
        row = {"sequence": i, "key": key, "description": description,
               "status": "QUEUED", "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        if i <= len(STEPS) and evidence_path.exists():
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            value = lookup(evidence, evidence_key)
            row["status"] = "PASS" if value is True or value == "PASS" else str(value).upper()
            row["evidence"] = evidence_file
            row["evidence_key"] = evidence_key
            if row["status"] not in ("PASS", "TRUE"):
                row["reason"] = "Evidence exists but the check is not a passing result; no claim was promoted."
        elif i <= len(STEPS):
            row["status"] = "BLOCKED"
            row["reason"] = f"Missing evidence: {evidence_file}"
        else:
            row["reason"] = "Queued for a later bounded iteration; no legacy task is stopped or overwritten."
        if args.status is not None and i <= len(STEPS):
            row["status"] = args.status
            row["override"] = True
        ledger.append(row)
    report = {"schema": "clawstack.improvement_chain.v1", "requested_steps": 50,
              "executed_steps": sum(x["status"] not in ("QUEUED", "BLOCKED") for x in ledger),
              "queued_steps": sum(x["status"] == "QUEUED" for x in ledger),
              "ledger": ledger,
              "policy": "never overwrite or stop legacy jobs; each step requires evidence"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
