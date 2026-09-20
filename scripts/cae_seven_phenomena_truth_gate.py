"""Fail-closed truth gate for one arbitrary-3D, seven-phenomena CAE run.

The gate separates numerical completion from engineering validation.  A run
using virtual material data may pass every numerical check, but it remains an
uncalibrated screening result and is never promoted to production completion.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


PHENOMENA = (
    "fill",
    "warpage",
    "shrinkage",
    "sink",
    "void",
    "airtrap",
    "weldline",
)

PHYSICS_LEVELS = {"direct", "coupled", "proxy", "candidate"}
PRODUCTION_PHYSICS_LEVELS = {"direct", "coupled"}

REQUIRED_SOLVERS = {
    "fill": {"openfoam"},
    "warpage": {"calculix", "elmer"},
    "shrinkage": {"calculix", "elmer"},
    "sink": {"calculix", "elmer"},
    "void": {"openfoam", "calculix", "elmer"},
    "airtrap": {"openfoam"},
    "weldline": {"openfoam"},
}

REQUIRED_EVIDENCE = {
    "fill": ("volume_fraction_history", "full_fill_metrics"),
    "warpage": ("displacement_field", "stress_field", "cooling_history"),
    "shrinkage": ("volumetric_shrinkage_field", "solidification_history"),
    "sink": ("surface_depression_field", "thickness_cooling_gradient"),
    "void": (
        "void_fraction_field",
        "nucleation_growth_transport",
        "coalescence_history",
        "stress_feedback",
    ),
    "airtrap": (
        "gas_volume_fraction_field",
        "vent_mass_flow_history",
        "trapped_component_history",
    ),
    "weldline": (
        "front_arrival_field",
        "collision_angle_field",
        "persistent_weld_map",
    ),
}

SOLVER_ARTIFACTS = {
    "openfoam": ("log", "history_manifest", "final_fields"),
    "calculix": ("log", "frd", "dat"),
    "elmer": ("log", "result"),
}

GLOBAL_CONVERGENCE_CHECKS = (
    "spatial",
    "temporal",
    "conservation",
    "cross_solver",
)

ENGINEERING_VALIDATION_CHECKS = (
    "reference_validity",
    "reproducibility",
    "independent_review",
    "uncertainty_reported",
    "provenance_complete",
)


def _is_pass(value: Any) -> bool:
    if value is True:
        return True
    return isinstance(value, str) and value.strip().upper() in {
        "PASS",
        "PASSED",
        "COMPLETE",
        "COMPLETED",
        "CONVERGED",
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _resolve_path(value: Any, base_dir: Path) -> Path | None:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        return None
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _artifact_exists(value: Any, base_dir: Path) -> bool:
    if isinstance(value, Mapping):
        value = value.get("path", value.get("artifact"))
    path = _resolve_path(value, base_dir)
    return bool(path and path.is_file() and path.stat().st_size > 0)


def _load_component(
    value: Any,
    base_dir: Path,
    label: str,
    failed: list[str],
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    path = _resolve_path(value, base_dir)
    if path is None or not path.is_file():
        failed.append(f"{label}.manifest_missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        failed.append(f"{label}.manifest_invalid")
        return {}
    if not isinstance(payload, Mapping):
        failed.append(f"{label}.manifest_not_object")
        return {}
    return payload


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdefABCDEF" for character in value)


def _check_identity(
    label: str,
    component: Mapping[str, Any],
    canonical: Mapping[str, str],
    failed: list[str],
) -> None:
    for key, expected in canonical.items():
        actual = component.get(key)
        if actual != expected:
            failed.append(f"identity.{label}.{key}_mismatch")


def _check_artifacts(
    label: str,
    artifacts: Any,
    required: Iterable[str],
    base_dir: Path,
    failed: list[str],
) -> None:
    artifact_map = _as_mapping(artifacts)
    for name in required:
        if not _artifact_exists(artifact_map.get(name), base_dir):
            failed.append(f"{label}.artifact.{name}_missing_or_empty")


def _check_solver(
    name: str,
    manifest: Mapping[str, Any],
    canonical: Mapping[str, str],
    base_dir: Path,
    failed: list[str],
) -> None:
    label = f"solver.{name}"
    _check_identity(label, manifest, canonical, failed)
    if str(manifest.get("execution_mode", "")).strip().lower() != "actual_solve":
        failed.append(f"{label}.not_actual_solve")
    if manifest.get("returncode") != 0:
        failed.append(f"{label}.returncode_not_zero")
    if not _is_pass(manifest.get("status")):
        failed.append(f"{label}.status_not_pass")
    if not _is_pass(_as_mapping(manifest.get("convergence")).get("status")):
        failed.append(f"{label}.convergence_not_pass")
    if not str(manifest.get("solver_version", "")).strip():
        failed.append(f"{label}.solver_version_missing")
    _check_artifacts(
        label,
        manifest.get("artifacts"),
        SOLVER_ARTIFACTS[name],
        base_dir,
        failed,
    )


def _check_openfoam_history(manifest: Mapping[str, Any], failed: list[str]) -> None:
    if str(manifest.get("history_source", "")).strip().lower() != "actual_solver":
        failed.append("solver.openfoam.history_source_not_actual_solver")
    if manifest.get("synthetic") is not False:
        failed.append("solver.openfoam.synthetic_flag_not_false")
    if manifest.get("history_complete") is not True:
        failed.append("solver.openfoam.history_not_complete")
    try:
        count = int(manifest.get("history_time_count", 0))
    except (TypeError, ValueError):
        count = 0
    if count < 2:
        failed.append("solver.openfoam.history_time_count_lt_2")

    fields = {str(field).strip().lower() for field in manifest.get("fields", [])}
    if "alpha.polymer" in fields:
        fields.add("alpha")
    for field in ("t", "p", "alpha", "u", "rho"):
        if field not in fields:
            failed.append(f"solver.openfoam.field.{field}_missing")
    if manifest.get("same_mesh_same_times") is not True:
        failed.append("solver.openfoam.fields_not_same_mesh_same_times")

    full_fill = _as_mapping(manifest.get("full_fill_gate"))
    if not _is_pass(full_fill.get("status")):
        failed.append("solver.openfoam.full_fill_gate_not_pass")
    if full_fill.get("bounded_alpha") is not True:
        failed.append("solver.openfoam.alpha_not_bounded")
    if not _is_pass(full_fill.get("mass_balance_status")):
        failed.append("solver.openfoam.mass_balance_not_pass")
    try:
        final_mean_alpha = float(full_fill.get("final_mean_alpha", -1.0))
        minimum_region_alpha = float(full_fill.get("minimum_region_alpha", -1.0))
    except (TypeError, ValueError):
        final_mean_alpha = -1.0
        minimum_region_alpha = -1.0
    if not 0.999 <= final_mean_alpha <= 1.0:
        failed.append("solver.openfoam.final_mean_alpha_not_full")
    if not 0.99 <= minimum_region_alpha <= 1.0:
        failed.append("solver.openfoam.minimum_region_alpha_not_full")


def _check_phenomenon(
    name: str,
    manifest: Mapping[str, Any],
    canonical: Mapping[str, str],
    base_dir: Path,
    failed: list[str],
) -> dict[str, Any]:
    label = f"phenomenon.{name}"
    start = len(failed)
    _check_identity(label, manifest, canonical, failed)

    level = str(manifest.get("physics_level", "")).strip().lower()
    if level not in PHYSICS_LEVELS:
        failed.append(f"{label}.physics_level_invalid")
    elif level not in PRODUCTION_PHYSICS_LEVELS:
        failed.append(f"{label}.physics_level_{level}_not_production")

    if not _is_pass(manifest.get("solve_status")):
        failed.append(f"{label}.solve_status_not_pass")
    if not _is_pass(_as_mapping(manifest.get("convergence")).get("status")):
        failed.append(f"{label}.convergence_not_pass")

    solver_runs = {
        str(solver).strip().lower() for solver in manifest.get("solver_runs", [])
    }
    for solver in sorted(REQUIRED_SOLVERS[name] - solver_runs):
        failed.append(f"{label}.solver.{solver}_missing")

    evidence = _as_mapping(manifest.get("evidence"))
    for evidence_name in REQUIRED_EVIDENCE[name]:
        if not _artifact_exists(evidence.get(evidence_name), base_dir):
            failed.append(f"{label}.evidence.{evidence_name}_missing_or_empty")

    return {
        "physics_level": level or "missing",
        "verdict": "PASS" if len(failed) == start else "HOLD",
        "failed_checks": failed[start:],
    }


def _next_actions(failed: Iterable[str]) -> list[str]:
    actions: list[str] = []
    codes = list(failed)
    if any(code.startswith("identity.") for code in codes):
        actions.append("Regenerate every manifest from the same immutable geometry, mesh, and history bundle.")
    if any(code.startswith("solver.openfoam.history") or "full_fill" in code or "alpha_" in code for code in codes):
        actions.append("Run a multi-time, actual OpenFOAM history through the strict full-fill and boundedness gate.")
    if any(code.startswith("solver.calculix") for code in codes):
        actions.append("Run CalculiX, retain non-empty FRD/DAT/log artifacts, and prove convergence.")
    if any(code.startswith("solver.elmer") for code in codes):
        actions.append("Run the independent Elmer solve, retain its result/log artifacts, and prove convergence.")
    if any("physics_level_proxy" in code or "physics_level_candidate" in code for code in codes):
        actions.append("Replace every proxy or candidate phenomenon with direct or coupled solver evidence.")
    if any("evidence." in code for code in codes):
        actions.append("Export the required spatial and time-resolved evidence artifacts for each held phenomenon.")
    if any(code.startswith("convergence.") or ".convergence_" in code for code in codes):
        actions.append("Complete spatial, temporal, conservation, and cross-solver convergence checks.")
    if any(code.startswith("validation.") or code.startswith("material.") for code in codes):
        actions.append("Calibrate measured material data and complete independent reference validation.")
    if not actions and codes:
        actions.append("Correct the failed checks and rerun this gate without weakening its requirements.")
    return actions


def evaluate_bundle(bundle: Mapping[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    """Evaluate a seven-phenomena bundle and return a fail-closed report."""
    base = Path.cwd() if base_dir is None else Path(base_dir)
    failed: list[str] = []

    geometry_sha256 = bundle.get("geometry_sha256")
    mesh_sha256 = bundle.get("mesh_sha256")
    history_id = bundle.get("history_id")
    if not _valid_sha256(geometry_sha256):
        failed.append("bundle.geometry_sha256_invalid")
    if not _valid_sha256(mesh_sha256):
        failed.append("bundle.mesh_sha256_invalid")
    if not isinstance(history_id, str) or len(history_id.strip()) < 8:
        failed.append("bundle.history_id_invalid")
    canonical = {
        "geometry_sha256": str(geometry_sha256 or ""),
        "mesh_sha256": str(mesh_sha256 or ""),
        "history_id": str(history_id or ""),
    }

    solvers = _as_mapping(bundle.get("solvers"))
    solver_manifests: dict[str, Mapping[str, Any]] = {}
    for name in SOLVER_ARTIFACTS:
        manifest = _load_component(
            solvers.get(name), base, f"solver.{name}", failed
        )
        solver_manifests[name] = manifest
        _check_solver(name, manifest, canonical, base, failed)
    _check_openfoam_history(solver_manifests.get("openfoam", {}), failed)

    convergence = _as_mapping(bundle.get("convergence"))
    for name in GLOBAL_CONVERGENCE_CHECKS:
        if not _is_pass(convergence.get(name)):
            failed.append(f"convergence.{name}_not_pass")

    phenomenon_values = _as_mapping(bundle.get("phenomena"))
    phenomenon_results: dict[str, dict[str, Any]] = {}
    for name in PHENOMENA:
        manifest = _load_component(
            phenomenon_values.get(name), base, f"phenomenon.{name}", failed
        )
        phenomenon_results[name] = _check_phenomenon(
            name, manifest, canonical, base, failed
        )

    material = _as_mapping(bundle.get("material"))
    material_kind = str(material.get("kind", "")).strip().lower()
    validation = _as_mapping(bundle.get("validation"))
    if material_kind == "measured":
        if not _is_pass(material.get("calibration_status")):
            failed.append("material.measured_calibration_not_pass")
        for name in ENGINEERING_VALIDATION_CHECKS:
            if not _is_pass(validation.get(name)):
                failed.append(f"validation.{name}_not_pass")
    elif material_kind != "virtual":
        failed.append("material.kind_must_be_virtual_or_measured")

    failed = list(dict.fromkeys(failed))
    numerically_complete = not failed
    if failed:
        verdict = "HOLD"
        status = "HOLD"
        engineering_validated = False
        production_complete = False
    elif material_kind == "virtual":
        verdict = "PASS"
        status = "NUMERICALLY_COMPLETE_UNCALIBRATED"
        engineering_validated = False
        production_complete = False
    else:
        verdict = "PASS"
        status = "ENGINEERING_VALIDATED"
        engineering_validated = True
        production_complete = True

    return {
        "schema": "clawstack.cae.seven_phenomena_truth_gate.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "status": status,
        "numerically_complete": numerically_complete,
        "engineering_validated": engineering_validated,
        "production_complete": production_complete,
        "production_promotion_allowed": production_complete,
        "material_kind": material_kind or "missing",
        "canonical_identity": canonical,
        "phenomena": phenomenon_results,
        "failed_checks": failed,
        "next_actions": _next_actions(failed),
        "limitations": (
            ["Virtual material data are not measured calibration data."]
            if status == "NUMERICALLY_COMPLETE_UNCALIBRATED"
            else []
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        bundle = json.loads(args.bundle_json.read_text(encoding="utf-8-sig"))
        if not isinstance(bundle, Mapping):
            raise ValueError("top-level bundle must be a JSON object")
        report = evaluate_bundle(bundle, args.bundle_json.resolve().parent)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "schema": "clawstack.cae.seven_phenomena_truth_gate.v1",
            "verdict": "HOLD",
            "status": "HOLD",
            "numerically_complete": False,
            "engineering_validated": False,
            "production_complete": False,
            "production_promotion_allowed": False,
            "failed_checks": [f"bundle.invalid:{type(exc).__name__}:{exc}"],
            "next_actions": ["Repair the bundle JSON and rerun the truth gate."],
        }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
