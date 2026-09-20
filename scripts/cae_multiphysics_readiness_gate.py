"""Readiness gate for arbitrary OpenFOAM -> CalculiX/Elmer molding runs.

The gate is intentionally conservative.  It does not claim solver completion;
it verifies that the code path has enough evidence to advance each subsystem
without waiting for a long Vivobook OpenFOAM run to finish.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import material_chain
    import wait_cae_history_inputs
    from cae_multiphysics_contract import validate_calibration, validate_openfoam_run_manifest
except ImportError:  # direct execution from outside scripts/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import material_chain
    import wait_cae_history_inputs
    from cae_multiphysics_contract import validate_calibration, validate_openfoam_run_manifest


REQUIRED_BOUNDARY_ROLES = ("gate", "vent", "wall")
REQUIRED_HISTORY_FIELDS = tuple(wait_cae_history_inputs.REQUIRED)


def _load_json(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le"):
        try:
            return json.loads(data.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(data.decode("utf-8", errors="replace"))


def _status(ok: bool, ready: str = "PASS") -> str:
    return ready if ok else "HOLD"


def _missing_paths(paths: list[Path]) -> list[str]:
    return [str(p) for p in paths if not p.exists()]


def check_openfoam_case(case_dir: Path) -> dict[str, Any]:
    required = [
        case_dir / "system" / "controlDict",
        case_dir / "system" / "fvSolution",
        case_dir / "system" / "fvSchemes",
        case_dir / "constant" / "polyMesh" / "boundary",
        case_dir / "constant" / "transportProperties",
        case_dir / "constant" / "thermophysicalProperties.polymer",
        case_dir / "0" / "T",
        case_dir / "0" / "U",
        case_dir / "0" / "alpha.polymer",
    ]
    missing = _missing_paths(required)
    control = (case_dir / "system" / "controlDict").read_text(encoding="utf-8", errors="replace") if not missing else ""
    thermo = (case_dir / "constant" / "thermophysicalProperties.polymer").read_text(encoding="utf-8", errors="replace") if (case_dir / "constant" / "thermophysicalProperties.polymer").exists() else ""
    guards = {
        "runTimeModifiable": "runTimeModifiable true" in control,
        "adjustTimeStep": "adjustTimeStep yes" in control,
        "maxCo": "maxCo" in control,
        "maxAlphaCo": "maxAlphaCo" in control,
        "maxDeltaT": "maxDeltaT" in control,
        "compressible_thermo": "equationOfState" in thermo,
    }
    return {
        "status": _status(not missing and all(guards.values())),
        "missing": missing,
        "guards": guards,
    }


def check_cross_wlf(plan: dict[str, Any]) -> dict[str, Any]:
    guards = plan.get("guards", {})
    ok = (
        plan.get("status") in {"DESIGN_CARD_READY_CUSTOM_LIBRARY_REQUIRED", "READY_FOR_CASE_INJECTION", "PASS"}
        and float(guards.get("nu_min", 0.0)) > 0.0
        and float(guards.get("nu_max", 0.0)) > float(guards.get("nu_min", 0.0))
        and float(guards.get("shear_rate_min", 0.0)) >= 0.0
        and float(guards.get("shear_rate_max", 0.0)) > float(guards.get("shear_rate_min", 0.0))
    )
    return {
        "status": _status(ok, "READY_TO_RECONNECT"),
        "bounded_transport_card": bool(plan),
        "guards": guards,
        "note": "custom OpenFOAM transport library compile/run remains separate",
    }


def check_material_models(calibration: dict[str, Any]) -> dict[str, Any]:
    tait = material_chain.TaitTwoDomain(
        rho_ref=900.0,
        t_ref=508.0,
        alpha_melt=2.0e-4,
        alpha_solid=7.0e-5,
        transition_k=393.15,
        width_k=5.0,
        B_melt=2.0e8,
        B_solid=4.0e8,
    )
    cross = material_chain.CrossWLF(
        n=0.35,
        tau_star_pa=5.0e4,
        d1_pa_s=1.0e10,
        d2_k=378.15,
        d3_k_pa=0.0,
        a1=17.44,
        a2_k=51.6,
    )
    rho_low = tait.density(101325.0, 508.0)
    rho_high = tait.density(5.0e7, 508.0)
    eta_low_shear = cross.viscosity(1.0, 508.0, 101325.0)
    eta_high_shear = cross.viscosity(1.0e4, 508.0, 101325.0)
    material_checks = {
        "tait_density_positive": rho_low > 0.0 and rho_high > 0.0,
        "tait_density_increases_with_pressure": rho_high > rho_low,
        "cross_wlf_positive": eta_low_shear > 0.0 and eta_high_shear > 0.0,
        "cross_wlf_shear_thinning": eta_high_shear < eta_low_shear,
    }
    return {
        "status": _status(all(material_checks.values())),
        "checks": material_checks,
        "calibration": validate_calibration(calibration),
    }


def check_resume_and_checkpoint(case_dir: Path, monitor_report: dict[str, Any]) -> dict[str, Any]:
    if monitor_report:
        progress = monitor_report.get("progress", {})
        eta_seconds = progress.get("estimated_remaining_wall_seconds")
        if isinstance(eta_seconds, (int, float)) and eta_seconds > 7 * 86400:
            runtime_classification = "RUNNING_IMPRACTICAL_ETA"
        elif isinstance(eta_seconds, (int, float)) and eta_seconds >= 0:
            runtime_classification = "RUNNING_BOUNDED_ETA"
        else:
            runtime_classification = "ETA_UNAVAILABLE"
        ok = (
            monitor_report.get("status") in {"RUNNING", "COMPLETED", "RESTART_GRACE"}
            and bool(monitor_report.get("latest_complete_checkpoint"))
            and not progress.get("active_error_markers")
        )
        return {
            "status": _status(ok, "CHECKPOINT_READY"),
            "source": "monitor_report",
            "running_process_detected": bool(monitor_report.get("running_process_detected")),
            "latest_complete_checkpoint": monitor_report.get("latest_complete_checkpoint"),
            "active_error_markers": progress.get("active_error_markers", []),
            "runtime_classification": runtime_classification,
            "progress": {
                "time_s": progress.get("last_time_s"),
                "target_time_s": progress.get("target_time_s"),
                "alpha_mean": progress.get("last_alpha_mean"),
                "delta_t_s": progress.get("last_delta_t_s"),
                "courant_max": progress.get("last_courant_max"),
                "interface_courant_max": progress.get("last_interface_courant_max"),
                "estimated_remaining_wall_seconds": progress.get("estimated_remaining_wall_seconds"),
            },
        }
    fallback = wait_cae_history_inputs.check(case_dir, min_time=0.0, min_frames=1)
    return {
        "status": _status(fallback["status"] == "READY", "CHECKPOINT_READY"),
        "source": "local_history_probe",
        "latest_complete_time_s": fallback["latest_complete_time_s"],
        "complete_frame_count": fallback["complete_frame_count"],
    }


def check_history_transfer(case_dir: Path, coupling_package: dict[str, Any]) -> dict[str, Any]:
    history = wait_cae_history_inputs.check(case_dir, min_time=0.0, min_frames=1)
    package_status = coupling_package.get("calculix_package", {}).get("status")
    transfer_mode = coupling_package.get("calculix_package", {}).get("transfer_mode")
    ok = history["status"] == "READY" and package_status in {"INPUT_READY", "PACKAGED_NOT_SOLVED", None}
    if coupling_package:
        ok = ok and bool(transfer_mode)
    return {
        "status": _status(ok, "TRANSFER_INPUT_READY"),
        "history": history,
        "coupling_package_status": package_status,
        "transfer_mode": transfer_mode,
    }


def check_downstream_solvers(coupling_package: dict[str, Any]) -> dict[str, Any]:
    ccx = coupling_package.get("calculix_package", {})
    elmer = coupling_package.get("elmer_package", {})
    ccx_input_ready = ccx.get("status") in {"INPUT_READY", "PACKAGED_NOT_SOLVED", "SOLVED"}
    elmer_input_ready = elmer.get("status") in {"INPUT_READY_NOT_SOLVED", "INPUT_READY", "SOLVED"}
    ok = bool(coupling_package) and ccx_input_ready and elmer_input_ready
    return {
        "status": _status(ok, "DOWNSTREAM_INPUT_READY"),
        "calculix": ccx,
        "elmer": elmer,
        "checks": {
            "calculix_input_ready": ccx_input_ready,
            "elmer_input_ready": elmer_input_ready,
            "same_manifest": bool(coupling_package),
        },
        "note": "solve execution and FRD/DAT or Elmer result verification remain separate unless status is SOLVED",
    }


def check_video_pipeline(video_manifest: dict[str, Any]) -> dict[str, Any]:
    required = ("resin_fill", "warpage", "shrinkage", "sink", "void", "airtrap", "weldline")
    videos = video_manifest.get("videos", {}) if video_manifest else {}
    checks = {
        key: bool(videos.get(key, {}).get("path") or videos.get(key))
        for key in required
    }
    per_video_motion = {
        key: bool(
            isinstance(videos.get(key), dict)
            and videos[key].get("moving_frames_verified")
            and float(videos[key].get("frame_delta_fraction", 0.0)) > 0.0
        )
        for key in required
    }
    per_video_labels = {
        key: bool(isinstance(videos.get(key), dict) and videos[key].get("interpretation_label"))
        for key in required
    }
    qc = video_manifest.get("visual_qc", {}) if video_manifest else {}
    moving = qc.get("moving_frames_verified", False) and all(per_video_motion.values())
    annotated = qc.get("contour_interpretation_labels", False) and all(per_video_labels.values())
    return {
        "status": _status(bool(video_manifest) and all(checks.values()) and moving and annotated, "VIDEO_QA_READY"),
        "checks": checks,
        "per_video_motion": per_video_motion,
        "per_video_labels": per_video_labels,
        "visual_qc": {"moving_frames_verified": bool(moving), "contour_interpretation_labels": bool(annotated)},
        "note": "Global QA flags are insufficient: every phenomenon needs measured frame change and an interpretation label.",
    }


def check_boundary_generalization(boundary_config: dict[str, Any]) -> dict[str, Any]:
    if boundary_config.get("schema") == "clawstack.arbitrary.boundary.groups.v1":
        topology_checks = boundary_config.get("surface_topology", {}).get("checks", {})
        groups = boundary_config.get("groups", {})
        roles = boundary_config.get("roles", {})
        patches = boundary_config.get("openfoam_artifacts", {}).get("patches", {})
        gate_groups = [name for name in roles.get("gate", ()) if groups.get(name)]
        vent_groups = [name for name in roles.get("vent", ()) if groups.get(name)]
        wall_groups = [name for name in roles.get("wall", ()) if groups.get(name)]
        if not roles:
            gate_groups = [name for name, ids in groups.items() if name.startswith("gate") and ids]
            vent_groups = [name for name, ids in groups.items() if name.startswith("vent") and ids]
            wall_groups = [name for name, ids in groups.items() if name.endswith("wall") and ids]
        contract_checks = {
            "extractor_pass": boundary_config.get("status") == "PASS",
            "watertight": topology_checks.get("watertight") is True,
            "manifold": topology_checks.get("manifold") is True,
            "orientation_consistent": topology_checks.get("orientation_consistent") is True,
            "nonzero_enclosed_volume": topology_checks.get("nonzero_enclosed_volume") is True,
            "model_fingerprint": bool(boundary_config.get("model", {}).get("sha256")),
            "spec_fingerprint": bool(boundary_config.get("spec", {}).get("sha256")),
            "gate_nonempty": bool(gate_groups),
            "vent_nonempty": bool(vent_groups),
            "wall_nonempty": bool(wall_groups),
            "patch_artifacts_complete": all(name in patches for name in gate_groups + vent_groups + wall_groups),
        }
        return {
            "status": _status(all(contract_checks.values()), "BOUNDARY_CONTRACT_READY"),
            "contract_checks": contract_checks,
            "groups": {"gate": gate_groups, "vent": vent_groups, "wall": wall_groups},
            "note": "Patch face count and area still require post-mesh reconciliation before solver promotion.",
        }

    roles = boundary_config.get("roles", {}) if boundary_config else {}
    role_checks = {role: bool(roles.get(role)) for role in REQUIRED_BOUNDARY_ROLES}
    gate = roles.get("gate", {})
    vent = roles.get("vent", {})
    shape_checks = {
        "gate_has_area_or_faces": bool(gate.get("area_m2") or gate.get("patches") or gate.get("face_groups")),
        "vent_has_area_or_faces": bool(vent.get("area_m2") or vent.get("patches") or vent.get("face_groups")),
        "coordinate_free": boundary_config.get("selection_mode") in {"mesh_groups", "patch_names", "feature_tags"},
    }
    return {
        "status": "HOLD",
        "role_checks": role_checks,
        "shape_checks": shape_checks,
        "note": "A declarative role list is not geometry evidence; provide a validated BoundaryContract manifest.",
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load_json(args.openfoam_manifest)
    coupling_package = _load_json(args.coupling_package)
    calibration = _load_json(args.calibration)
    cross_plan = _load_json(args.cross_plan)
    monitor_report = _load_json(args.monitor_report)
    video_manifest = _load_json(args.video_manifest)
    boundary_config = _load_json(args.boundary_config)
    stages = {
        "openfoam_case_generation_hardened": check_openfoam_case(args.case),
        "bounded_cross_wlf_reconnection_ready": check_cross_wlf(cross_plan),
        "tait_pvt_density_viscosity_unit_verified": check_material_models(calibration),
        "failure_resume_checkpoint_verified": check_resume_and_checkpoint(args.case, monitor_report),
        "openfoam_to_calculix_elmer_conservative_transfer": check_history_transfer(args.case, coupling_package),
        "calculix_elmer_wait_and_smoke_inputs": check_downstream_solvers(coupling_package),
        "video_visual_qa_report_pipeline": check_video_pipeline(video_manifest),
        "arbitrary_3d_boundary_generalization": check_boundary_generalization(boundary_config),
    }
    run_gate = validate_openfoam_run_manifest(manifest) if manifest else {"status": "NO_MANIFEST"}
    all_ready = all(stage["status"] not in {"HOLD"} for stage in stages.values())
    report = {
        "schema": "clawstack.cae.multiphysics.readiness.v1",
        "status": "READY_FOR_LONG_SOLVER_CHAIN" if all_ready and run_gate.get("status") == "PASS" else "IMPROVEMENT_READY_NOT_FULL_PRODUCTION",
        "case": str(args.case.resolve()),
        "openfoam_run_gate": run_gate,
        "stages": stages,
        "next_actions": [
            name for name, stage in stages.items() if stage["status"] == "HOLD"
        ],
        "limitations": [
            "A PASS here means the code path is wired and testable; it is not measured-material validation.",
            "OpenFOAM full-fill, ccx solve, Elmer solve, and video delivery remain separate runtime evidence.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--openfoam-manifest", type=Path)
    parser.add_argument("--cross-plan", type=Path)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--monitor-report", type=Path)
    parser.add_argument("--coupling-package", type=Path)
    parser.add_argument("--video-manifest", type=Path)
    parser.add_argument("--boundary-config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args)
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "READY_FOR_LONG_SOLVER_CHAIN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
