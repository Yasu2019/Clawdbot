"""Strict field and coupling contracts for arbitrary OpenFOAM -> CCX/Elmer runs.

This module is intentionally solver-agnostic: it validates real exported
fields and refuses to label proxy/material data as calibrated results.  It is
the seam where a future OpenFOAM case runner can be connected safely.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    from openfoam_calculix_coupling import read_scalar_field
except ImportError:  # direct loading from a test or another working directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from openfoam_calculix_coupling import read_scalar_field


VECTOR_RE = re.compile(r"internalField\s+nonuniform\s+List<vector>\s+(\d+)\s*\((.*?)\)\s*;", re.S)
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")


def _snapshot_field_paths(directory: Path) -> tuple[dict[str, Path], list[str]]:
    """Resolve canonical field names while preserving the actual source name."""
    paths: dict[str, Path] = {}
    missing: list[str] = []
    for name in ("T", "p", "alpha", "U", "rho"):
        candidates = ("alpha", "alpha.polymer") if name == "alpha" else (name,)
        source = next((directory / candidate for candidate in candidates if (directory / candidate).is_file()), None)
        if source is None:
            missing.append("alpha (or alpha.polymer)" if name == "alpha" else name)
        else:
            paths[name] = source
    return paths, missing


def read_vector_field(path: str | Path) -> np.ndarray:
    text = Path(path).read_text(encoding="utf-8")
    match = VECTOR_RE.search(text)
    if not match:
        raise ValueError(f"unsupported OpenFOAM vector field: {path}")
    rows = re.findall(r"\(([^()]+)\)", match.group(2))
    values = np.asarray([[float(v) for v in row.split()] for row in rows], dtype=float)
    if len(values) != int(match.group(1)) or values.ndim != 2 or values.shape[1] != 3:
        raise ValueError(f"vector count/shape mismatch: {path}")
    if not np.isfinite(values).all():
        raise ValueError(f"non-finite vector field: {path}")
    return values


def read_openfoam_snapshot(time_dir: str | Path) -> dict:
    """Read T,p,alpha,U,rho from one time directory and enforce same cell count."""
    directory = Path(time_dir)
    names, missing = _snapshot_field_paths(directory)
    if missing:
        raise FileNotFoundError(f"missing required fields in {directory}: " + ", ".join(missing))
    fields = {
        "T": np.asarray(read_scalar_field(names["T"]), dtype=float),
        "p": np.asarray(read_scalar_field(names["p"]), dtype=float),
        "alpha": np.asarray(read_scalar_field(names["alpha"]), dtype=float),
        "rho": np.asarray(read_scalar_field(names["rho"]), dtype=float),
        "U": read_vector_field(names["U"]),
    }
    # OpenFOAM uniform fields are expanded only when the caller supplies cell count.
    counts = {key: len(value) for key, value in fields.items() if key != "U"}
    counts["U"] = len(fields["U"])
    if len(set(counts.values())) != 1:
        raise ValueError(f"field cell counts differ: {counts}")
    if not np.isfinite(np.concatenate([fields[key].ravel() for key in ("T", "p", "alpha", "rho", "U")])).all():
        raise ValueError("snapshot contains non-finite values")
    if np.any(fields["T"] <= 0) or np.any(fields["rho"] <= 0):
        raise ValueError("T and rho must be positive SI values")
    if np.any(fields["alpha"] < -1e-12) or np.any(fields["alpha"] > 1 + 1e-12):
        raise ValueError("alpha must be bounded in [0,1]")
    source_fields = {key: path.name for key, path in names.items()}
    return {
        "time_s": float(directory.name),
        "cell_count": counts["T"],
        "fields": fields,
        "source_fields": source_fields,
        "source_sha256": {
            source_fields[key]: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in names.items()
        },
    }


def numeric_time_dirs(case_dir: str | Path) -> list[Path]:
    """Return numeric OpenFOAM time directories in physical time order."""
    root = Path(case_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"case directory not found: {case_dir}")
    dirs: list[tuple[float, Path]] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        try:
            dirs.append((float(child.name), child))
        except ValueError:
            continue
    if not dirs:
        raise FileNotFoundError(f"no numeric OpenFOAM time directories under: {case_dir}")
    return [path for _, path in sorted(dirs, key=lambda item: item[0])]


def read_openfoam_history(case_dir: str | Path, *, required_fields: Sequence[str] = ("T", "p", "alpha", "U", "rho")) -> dict:
    """Read all complete T,p,alpha,U,rho snapshots from a case directory.

    The history is accepted only when every numeric time directory has the same
    required fields and the same cell count. This prevents mixing partially
    written solver output with completed snapshots.
    """
    snapshots = []
    incomplete: dict[str, list[str]] = {}
    for directory in numeric_time_dirs(case_dir):
        resolved, missing_all = _snapshot_field_paths(directory)
        missing = []
        for name in required_fields:
            canonical = "alpha" if name == "alpha.polymer" else name
            if canonical not in resolved:
                missing.append("alpha (or alpha.polymer)" if canonical == "alpha" else canonical)
        if missing_all and set(required_fields) == {"T", "p", "alpha", "U", "rho"}:
            missing = missing_all
        if missing:
            incomplete[directory.name] = missing
            continue
        snapshots.append(read_openfoam_snapshot(directory))
    if incomplete:
        raise FileNotFoundError(f"incomplete OpenFOAM time directories: {incomplete}")
    if not snapshots:
        raise FileNotFoundError(f"no complete OpenFOAM snapshots under: {case_dir}")
    counts = {snap["time_s"]: snap["cell_count"] for snap in snapshots}
    if len(set(counts.values())) != 1:
        raise ValueError(f"history cell counts differ: {counts}")
    times = [snap["time_s"] for snap in snapshots]
    if len(times) != len(set(times)):
        raise ValueError(f"duplicate time values in history: {times}")
    return {
        "schema": "clawstack.openfoam.history.v1",
        "case_dir": str(Path(case_dir).resolve()),
        "time_s": times,
        "cell_count": snapshots[0]["cell_count"],
        "fields": list(required_fields),
        "snapshots": snapshots,
        "source_fields": {
            f"{snap['time_s']:.12g}/{canonical}": source
            for snap in snapshots
            for canonical, source in snap["source_fields"].items()
        },
        "source_sha256": {
            f"{snap['time_s']:.12g}/{source}": snap["source_sha256"][source]
            for snap in snapshots
            for source in snap["source_sha256"]
        },
    }


def conservative_transfer(values: Sequence[float], source_volumes: Sequence[float], weights: np.ndarray) -> tuple[np.ndarray, dict]:
    """Map cell values with an explicit overlap matrix and preserve volume integral."""
    source = np.asarray(values, dtype=float)
    volumes = np.asarray(source_volumes, dtype=float)
    matrix = np.asarray(weights, dtype=float)
    if source.ndim != 1 or volumes.shape != source.shape or matrix.ndim != 2 or matrix.shape[1] != len(source):
        raise ValueError("source values, volumes and overlap matrix have incompatible shapes")
    if np.any(source < 0) or np.any(volumes <= 0) or np.any(matrix < 0):
        raise ValueError("conservative transfer inputs must be nonnegative")
    row_sum = matrix.sum(axis=1)
    if np.any(row_sum <= 0):
        raise ValueError("every target row needs positive overlap")
    normalized = matrix / row_sum[:, None]
    mapped = normalized @ source
    source_integral = float(np.dot(source, volumes))
    target_volumes = row_sum
    target_integral = float(np.dot(mapped, target_volumes))
    if source_integral:
        mapped *= source_integral / target_integral
    target_integral = float(np.dot(mapped, target_volumes))
    return mapped, {"method": "explicit_overlap_volume_corrected", "conservative": True,
                    "source_integral": source_integral, "target_integral": target_integral,
                    "relative_error": abs(target_integral-source_integral)/max(abs(source_integral), 1e-300)}


def conservative_transfer_sparse(values: Sequence[float], source_volumes: Sequence[float],
                                 target_indices: Sequence[int], source_indices: Sequence[int],
                                 overlap_volumes: Sequence[float], *, target_count: int | None = None) -> tuple[np.ndarray, dict]:
    """Map cell values with sparse COO overlap volumes and preserve integral."""
    source = np.asarray(values, dtype=float)
    volumes = np.asarray(source_volumes, dtype=float)
    tgt = np.asarray(target_indices, dtype=int)
    src = np.asarray(source_indices, dtype=int)
    ov = np.asarray(overlap_volumes, dtype=float)
    if source.ndim != 1 or volumes.shape != source.shape:
        raise ValueError("source values and volumes have incompatible shapes")
    if tgt.ndim != 1 or src.shape != tgt.shape or ov.shape != tgt.shape:
        raise ValueError("sparse overlap arrays have incompatible shapes")
    if len(ov) == 0 or np.any(src < 0) or np.any(src >= len(source)) or np.any(tgt < 0):
        raise ValueError("sparse overlap indices out of range")
    if np.any(source < 0) or np.any(volumes <= 0) or np.any(ov <= 0):
        raise ValueError("conservative transfer inputs must be nonnegative with positive volumes")
    n_target = int(target_count if target_count is not None else tgt.max() + 1)
    if n_target <= int(tgt.max()):
        raise ValueError("target_count is smaller than overlap index range")
    target_volumes = np.bincount(tgt, weights=ov, minlength=n_target)
    if np.any(target_volumes <= 0):
        raise ValueError("every target needs positive overlap")
    weighted = np.bincount(tgt, weights=source[src] * ov, minlength=n_target)
    mapped = weighted / target_volumes
    source_integral = float(np.dot(source, volumes))
    target_integral = float(np.dot(mapped, target_volumes))
    if source_integral:
        mapped *= source_integral / target_integral
    target_integral = float(np.dot(mapped, target_volumes))
    return mapped, {"method": "sparse_overlap_volume_corrected", "conservative": True,
                    "source_integral": source_integral, "target_integral": target_integral,
                    "relative_error": abs(target_integral-source_integral)/max(abs(source_integral), 1e-300),
                    "target_count": n_target, "overlap_entry_count": int(len(ov))}


def conservative_transfer_history(history: dict, field_name: str, source_volumes: Sequence[float],
                                  weights: np.ndarray) -> dict:
    """Transfer one scalar OpenFOAM field for every accepted time snapshot."""
    frames = []
    worst_error = 0.0
    for snap in history["snapshots"]:
        if field_name not in snap["fields"] or field_name == "U":
            raise ValueError(f"scalar field required for transfer: {field_name}")
        mapped, audit = conservative_transfer(snap["fields"][field_name], source_volumes, weights)
        worst_error = max(worst_error, float(audit["relative_error"]))
        frames.append({"time_s": snap["time_s"], "values": mapped, "audit": audit})
    return {
        "schema": "clawstack.conservative.transfer.history.v1",
        "field": field_name,
        "time_s": history["time_s"],
        "target_count": int(np.asarray(weights).shape[0]),
        "frames": frames,
        "worst_relative_error": worst_error,
        "conservative": worst_error <= 1e-10,
    }


def conservative_transfer_sparse_history(history: dict, field_name: str, source_volumes: Sequence[float],
                                         target_indices: Sequence[int], source_indices: Sequence[int],
                                         overlap_volumes: Sequence[float], *, target_count: int | None = None) -> dict:
    """Sparse-overlap variant of conservative transfer for large meshes."""
    frames = []
    worst_error = 0.0
    resolved_target_count = int(target_count if target_count is not None else np.asarray(target_indices, dtype=int).max() + 1)
    for snap in history["snapshots"]:
        if field_name not in snap["fields"] or field_name == "U":
            raise ValueError(f"scalar field required for transfer: {field_name}")
        mapped, audit = conservative_transfer_sparse(
            snap["fields"][field_name], source_volumes, target_indices, source_indices,
            overlap_volumes, target_count=resolved_target_count,
        )
        worst_error = max(worst_error, float(audit["relative_error"]))
        frames.append({"time_s": snap["time_s"], "values": mapped, "audit": audit})
    return {
        "schema": "clawstack.conservative.transfer.history.v1",
        "field": field_name,
        "time_s": history["time_s"],
        "target_count": resolved_target_count,
        "frames": frames,
        "worst_relative_error": worst_error,
        "conservative": worst_error <= 1e-10,
        "mapping": "sparse_overlap_volume_corrected",
    }


def direct_same_mesh_history(history: dict, field_name: str) -> dict:
    """Pass one scalar field through unchanged when source and target share cells.

    This is intentionally separate from overlap-matrix transfer.  It is useful
    for solver-chain smoke tests where the downstream target IDs are a direct
    one-to-one numbering of the accepted OpenFOAM cells.  The audit is still
    explicit so callers do not confuse this with geometric remapping.
    """
    frames = []
    for snap in history["snapshots"]:
        if field_name not in snap["fields"] or field_name == "U":
            raise ValueError(f"scalar field required for direct transfer: {field_name}")
        values = np.asarray(snap["fields"][field_name], dtype=float).copy()
        if len(values) != history["cell_count"]:
            raise ValueError(f"direct transfer count mismatch for {field_name}")
        frames.append({
            "time_s": snap["time_s"],
            "values": values,
            "audit": {
                "method": "same_mesh_identity",
                "source_integral": float(values.sum()),
                "target_integral": float(values.sum()),
                "absolute_error": 0.0,
                "relative_error": 0.0,
            },
        })
    return {
        "schema": "clawstack.conservative.transfer.history.v1",
        "field": field_name,
        "time_s": history["time_s"],
        "target_count": int(history["cell_count"]),
        "frames": frames,
        "worst_relative_error": 0.0,
        "conservative": True,
        "mapping": "same_mesh_identity",
    }


def build_calculix_history_package(*, temperature: dict, pressure: dict,
                                   eigenstrain: dict | None = None,
                                   reference_state: dict | None = None,
                                   constraints: dict | None = None) -> dict:
    """Assemble validated one-way history inputs for a CalculiX reanalysis."""
    ref = reference_state or {}
    if ref.get("stress_free_temperature_K") is None:
        raise ValueError("reference_state.stress_free_temperature_K is required")
    shrinkage_counting = ref.get("shrinkage_counting")
    if shrinkage_counting not in ("eigenstrain_only", "cte_only"):
        raise ValueError("reference_state.shrinkage_counting must be eigenstrain_only or cte_only")
    if shrinkage_counting == "eigenstrain_only" and eigenstrain is None:
        raise ValueError("eigenstrain history is required when shrinkage_counting=eigenstrain_only")
    if shrinkage_counting == "cte_only" and eigenstrain is not None:
        raise ValueError("eigenstrain history is forbidden when shrinkage_counting=cte_only")
    if (
        shrinkage_counting == "eigenstrain_only"
        and ref.get("eigenstrain_frame_semantics") != "total_from_stress_free"
    ):
        raise ValueError(
            "reference_state.eigenstrain_frame_semantics must be total_from_stress_free"
        )
    if shrinkage_counting == "eigenstrain_only" and ref.get("strain_measure") != "green_lagrange":
        raise ValueError("reference_state.strain_measure must be green_lagrange")
    if (
        shrinkage_counting == "eigenstrain_only"
        and ref.get("reference_configuration") != "stress_free_geometry"
    ):
        raise ValueError("reference_state.reference_configuration must be stress_free_geometry")
    if (
        shrinkage_counting == "eigenstrain_only"
        and ref.get("eigenstrain_value_kind") != "isotropic_normal_component"
    ):
        raise ValueError("reference_state.eigenstrain_value_kind must be isotropic_normal_component")

    histories = {"temperature_K": temperature, "pressure_Pa": pressure}
    if eigenstrain is not None:
        histories["eigenstrain"] = eigenstrain
    times = {name: tuple(hist.get("time_s", ())) for name, hist in histories.items()}
    if len(set(times.values())) != 1 or not next(iter(times.values()), ()):
        raise ValueError(f"CalculiX histories must share nonempty times: {times}")
    target_counts = {name: int(hist.get("target_count", -1)) for name, hist in histories.items()}
    if len(set(target_counts.values())) != 1 or next(iter(target_counts.values())) <= 0:
        raise ValueError(f"CalculiX histories must share positive target_count: {target_counts}")
    nonconservative = [name for name, hist in histories.items() if not hist.get("conservative")]
    if nonconservative:
        raise ValueError(f"nonconservative histories cannot drive CalculiX: {nonconservative}")
    expected_times = next(iter(times.values()))
    expected_count = next(iter(target_counts.values()))
    invalid_frames = []
    for name, history in histories.items():
        frames = history.get("frames", ())
        frame_times = tuple(frame.get("time_s") for frame in frames)
        if len(frames) != len(expected_times) or frame_times != expected_times:
            invalid_frames.append(f"{name}:frame_times")
            continue
        if any(np.asarray(frame.get("values", ()), dtype=float).shape != (expected_count,) for frame in frames):
            invalid_frames.append(f"{name}:frame_values")
            continue
        if any(not np.isfinite(np.asarray(frame["values"], dtype=float)).all() for frame in frames):
            invalid_frames.append(f"{name}:nonfinite")
    if invalid_frames:
        raise ValueError(f"CalculiX history frames do not match time/target_count metadata: {invalid_frames}")
    return {
        "schema": "clawstack.calculix.history.package.v1",
        "status": "INPUT_READY",
        "time_s": list(next(iter(times.values()))),
        "target_count": next(iter(target_counts.values())),
        "histories": histories,
        "reference_state": ref,
        "constraints": constraints or {"release": "not_specified"},
        "checks": {
            "same_times": True,
            "same_target_count": True,
            "conservative_transfer": True,
            "stress_free_reference_defined": True,
            "shrinkage_double_counting_guard": ref["shrinkage_counting"],
        },
        "limitations": [
            "package generation does not execute CalculiX",
            "constraint release semantics must still be checked in the deck",
            "engineering accuracy requires measured PVT/Cross-WLF/CTE calibration",
        ],
    }


def _finite_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _history_source_evidence_complete(source_sha256: object, times: Sequence[float]) -> bool:
    if not isinstance(source_sha256, dict) or not source_sha256:
        return False
    if not all(isinstance(key, str) and _is_sha256(value) for key, value in source_sha256.items()):
        return False
    for time_s in times:
        prefix = f"{time_s:.12g}/"
        names = {key[len(prefix):] for key in source_sha256 if key.startswith(prefix)}
        if not {"T", "p", "U", "rho"}.issubset(names) or not ({"alpha", "alpha.polymer"} & names):
            return False
    return True


def _mapping_sha256(values: dict[str, str]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_openfoam_run_manifest(manifest: dict) -> dict:
    """Fail closed unless a raw, completed, full-fill OpenFOAM run is evidenced."""
    required_fields = {"T", "p", "alpha", "U", "rho"}
    field_values = manifest.get("fields", ())
    fields = set(field_values) if isinstance(field_values, (list, tuple, set)) else set()

    raw_times = manifest.get("time_s", ())
    times: list[float] = []
    if isinstance(raw_times, (list, tuple)):
        parsed_times = [_finite_float(value) for value in raw_times]
        if all(value is not None for value in parsed_times):
            times = [float(value) for value in parsed_times if value is not None]
    multi_time = len(times) >= 2 and all(right > left for left, right in zip(times, times[1:]))
    history_count = manifest.get("history_time_count")
    history_count_matches = (
        type(history_count) is int
        and history_count == len(times)
        and history_count >= 2
    )

    alpha_min = _finite_float(manifest.get("alpha_min"))
    alpha_max = _finite_float(manifest.get("alpha_max"))
    alpha_mean = _finite_float(manifest.get("alpha_mean_final"))
    alpha_mean_min = _finite_float(manifest.get("final_alpha_mean_min"))
    filled_cell_alpha_min = _finite_float(manifest.get("filled_cell_alpha_min"))
    filled_fraction = _finite_float(manifest.get("filled_cell_fraction_final"))
    filled_fraction_min = _finite_float(manifest.get("filled_cell_fraction_min"))

    mass_error = _finite_float(manifest.get("mass_balance_relative_error"))
    mass_tolerance = _finite_float(manifest.get("mass_balance_tolerance"))
    energy_error = _finite_float(manifest.get("energy_balance_relative_error"))
    energy_tolerance = _finite_float(manifest.get("energy_balance_tolerance"))
    audit = manifest.get("balance_audit") if isinstance(manifest.get("balance_audit"), dict) else {}
    audit_mass = _finite_float(audit.get("mass_balance_relative_error"))
    audit_energy = _finite_float(audit.get("energy_balance_relative_error"))
    accepted_audit_sources = {"solver_function_object", "postprocess_integral"}

    execution = manifest.get("solver_execution_evidence")
    execution = execution if isinstance(execution, dict) else {}
    fatal_markers = execution.get("fatal_markers")
    solver_log_completion = (
        execution.get("completed") is True
        and execution.get("end_marker") is True
        and isinstance(execution.get("path"), str)
        and bool(execution.get("path"))
        and _is_sha256(execution.get("sha256"))
        and isinstance(fatal_markers, list)
        and not fatal_markers
        and execution.get("returncode") in (None, 0)
    )

    history_sources = manifest.get("history_source_sha256")
    history_sources_valid = _history_source_evidence_complete(history_sources, times)
    history_fingerprint = manifest.get("history_fingerprint_sha256")
    history_fingerprint_valid = (
        history_sources_valid
        and _is_sha256(history_fingerprint)
        and history_fingerprint == _mapping_sha256(history_sources)
    )
    mesh_files = manifest.get("mesh_fingerprint_files")
    mesh_fingerprint_valid = (
        _is_sha256(manifest.get("mesh_fingerprint_sha256"))
        and isinstance(mesh_files, list)
        and {"points", "faces", "owner", "boundary"}.issubset(set(mesh_files))
    )

    checks = {
        "schema": manifest.get("schema") == "clawstack.openfoam.production.history.v1",
        "completed": manifest.get("status") == "COMPLETED",
        "solver_identified": isinstance(manifest.get("solver"), str) and bool(manifest.get("solver")),
        "nonisothermal": manifest.get("nonisothermal") is True,
        "compressible": manifest.get("compressible") is True,
        "venting": manifest.get("venting") is True,
        "raw_source_kind": manifest.get("source_kind") == "raw_openfoam_solver_history",
        "not_synthetic": manifest.get("synthetic") is False,
        "not_proxy": manifest.get("proxy") is False,
        "raw_multi_time_history": multi_time,
        "history_count_matches": history_count_matches,
        "required_fields": required_fields.issubset(fields),
        "bounded_alpha": alpha_min is not None and alpha_max is not None and alpha_min >= -1e-8 and alpha_max <= 1.0 + 1e-8,
        "full_fill_alpha_mean": (
            alpha_mean is not None
            and alpha_mean_min is not None
            and 0.0 <= alpha_mean_min <= 1.0
            and alpha_mean_min <= alpha_mean <= 1.0 + 1e-8
        ),
        "filled_cell_fraction": (
            filled_cell_alpha_min is not None
            and 0.0 <= filled_cell_alpha_min <= 1.0
            and filled_fraction is not None
            and filled_fraction_min is not None
            and 0.0 <= filled_fraction_min <= 1.0
            and filled_fraction_min <= filled_fraction <= 1.0
        ),
        "solver_log_completion": solver_log_completion,
        "balance_audit_source": (
            audit.get("source") in accepted_audit_sources
            and isinstance(audit.get("source_path"), str)
            and bool(audit.get("source_path"))
            and _is_sha256(audit.get("source_sha256"))
        ),
        "balance_audit_consistent": (
            mass_error is not None
            and energy_error is not None
            and audit_mass is not None
            and audit_energy is not None
            and math.isclose(mass_error, audit_mass, rel_tol=0.0, abs_tol=1e-15)
            and math.isclose(energy_error, audit_energy, rel_tol=0.0, abs_tol=1e-15)
        ),
        "mass_balance": mass_error is not None and mass_tolerance is not None and mass_tolerance > 0.0 and abs(mass_error) <= mass_tolerance,
        "energy_balance": energy_error is not None and energy_tolerance is not None and energy_tolerance > 0.0 and abs(energy_error) <= energy_tolerance,
        "mesh_fingerprint": mesh_fingerprint_valid,
        "history_fingerprint": history_fingerprint_valid,
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "clawstack.openfoam.run.gate.v1",
        "status": "PASS" if not failed_checks else "HOLD",
        "checks": checks,
        "failed_checks": failed_checks,
        "solver": manifest.get("solver"),
        "case_dir": manifest.get("case_dir"),
        "limitations": [] if not failed_checks else ["raw completed full-fill OpenFOAM evidence is incomplete or unauthenticated"],
    }


def _frame_values(history: dict, frame_index: int) -> np.ndarray:
    return np.asarray(history["frames"][frame_index]["values"], dtype=float)


def write_calculix_history_deck(
    output_dir: str | Path,
    package: dict,
    target_ids: Sequence[int] | None = None,
    *,
    node_ids: Sequence[int] | None = None,
    element_ids: Sequence[int] | None = None,
    element_integration_points: dict[int, int] | None = None,
    pressure_faces: Sequence[Sequence[int]] | None = None,
) -> dict:
    """Write entity-safe CalculiX history inputs from a validated package."""
    if package.get("schema") != "clawstack.calculix.history.package.v1" or package.get("status") != "INPUT_READY":
        raise ValueError("validated CalculiX history package required")
    reference_state = package.get("reference_state")
    reference_state = reference_state if isinstance(reference_state, dict) else {}
    shrinkage_counting = reference_state.get("shrinkage_counting")
    if shrinkage_counting not in {"cte_only", "eigenstrain_only"}:
        raise ValueError("validated shrinkage_counting is required")

    if shrinkage_counting == "cte_only":
        if target_ids is not None and node_ids is not None:
            raise ValueError("specify only one of target_ids or node_ids for cte_only")
        if element_ids is not None or element_integration_points is not None:
            raise ValueError("cte_only accepts node_ids, not element IDs or integration-point metadata")
        ids = list(node_ids if node_ids is not None else target_ids or ())
        target_entity = "node"
        integration_points: dict[int, int] = {}
    else:
        if target_ids is not None or node_ids is not None:
            raise ValueError("eigenstrain_only requires explicit element_ids; nodal/ambiguous target IDs are forbidden")
        ids = list(element_ids or ())
        target_entity = "element"
        if not isinstance(element_integration_points, dict):
            raise ValueError("eigenstrain_only requires element_integration_points")
        integration_points = dict(element_integration_points)
        if set(integration_points) != set(ids):
            raise ValueError("element_integration_points must exactly match element_ids")
        if any(type(count) is not int or count <= 0 for count in integration_points.values()):
            raise ValueError("integration-point counts must be positive integers")
    if (
        len(ids) != package.get("target_count")
        or any(type(identifier) is not int or identifier <= 0 for identifier in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError(f"{target_entity}_ids must be unique positive IDs matching package target_count")
    has_eigenstrain = "eigenstrain" in package.get("histories", {})
    if shrinkage_counting == "eigenstrain_only" and not has_eigenstrain:
        raise ValueError("eigenstrain_only package is missing eigenstrain history")
    if shrinkage_counting == "cte_only" and has_eigenstrain:
        raise ValueError("cte_only package must not contain eigenstrain history")
    out = Path(output_dir)
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    files = []
    for i, time_s in enumerate(package["time_s"]):
        temp_k = _frame_values(package["histories"]["temperature_K"], i)
        pressure_pa = _frame_values(package["histories"]["pressure_Pa"], i)
        if len(temp_k) != len(ids) or len(pressure_pa) != len(ids):
            raise ValueError(f"history frame size does not match {target_entity}_ids")
        if shrinkage_counting == "cte_only":
            temp_path = out / f"temperature_{i:04d}.inc"
            temp_path.write_text(
                "** OpenFOAM mapped nodal temperature history, Celsius\n*TEMPERATURE, OP=NEW\n"
                + "".join(f"{node_id}, {value - 273.15:.12e}\n" for node_id, value in zip(ids, temp_k)),
                encoding="ascii",
            )
            temperature_key = "temperature_include"
        else:
            temp_path = out / f"temperature_element_{i:04d}.csv"
            temp_path.write_text(
                "element_id,temperature_K\n"
                + "".join(f"{element_id},{value:.12e}\n" for element_id, value in zip(ids, temp_k)),
                encoding="ascii",
            )
            temperature_key = "temperature_element_csv"
        pressure_path = out / f"pressure_{i:04d}.csv"
        pressure_path.write_text(
            f"{target_entity}_id,pressure_Pa\n"
            + "".join(f"{identifier},{value:.12e}\n" for identifier, value in zip(ids, pressure_pa)),
            encoding="ascii",
        )
        frame = {
            "time_s": float(time_s),
            temperature_key: temp_path.name,
            "pressure_csv": pressure_path.name,
        }
        if has_eigenstrain:
            eigen = _frame_values(package["histories"]["eigenstrain"], i)
            if len(eigen) != len(ids) or not np.isfinite(eigen).all():
                raise ValueError("eigenstrain frame size/values do not match element_ids")
            eigen_path = out / f"eigenstrain_{i:04d}.csv"
            eigen_path.write_text(
                "target_id,eigenstrain\n"
                + "".join(f"{element_id},{value:.12e}\n" for element_id, value in zip(ids, eigen)),
                encoding="ascii",
            )
            frame["eigenstrain_csv"] = eigen_path.name
        files.append(frame)
    manifest = {
        "schema": "clawstack.calculix.deck.export.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "frames": files,
        "target_count": len(ids),
        "target_entity": target_entity,
        "element_integration_points": (
            {str(element_id): integration_points[element_id] for element_id in ids}
            if shrinkage_counting == "eigenstrain_only"
            else None
        ),
        "reference_state": package["reference_state"],
        "constraints": package["constraints"],
        "pressure_faces": [list(face) for face in pressure_faces] if pressure_faces else [],
        "limitations": [
            "include files written only; ccx execution and FRD/DAT verification still required",
            *(
                ["element-mapped physical temperature is audit-only until a separate nodal temperature map is supplied"]
                if shrinkage_counting == "eigenstrain_only"
                else []
            ),
        ],
    }
    (out / "calculix_history_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    return manifest


def build_elmer_comparison_package(package: dict, *, solver: str = "ElmerSolver") -> dict:
    """Create an independent-comparison contract for the same accepted history."""
    if package.get("schema") != "clawstack.calculix.history.package.v1" or package.get("status") != "INPUT_READY":
        raise ValueError("validated history package required")
    return {
        "schema": "clawstack.elmer.comparison.package.v1",
        "status": "INPUT_READY_NOT_SOLVED",
        "solver": solver,
        "time_s": list(package["time_s"]),
        "target_count": package["target_count"],
        "fields": ["temperature_K", "pressure_Pa"],
        "comparison_policy": "same accepted OpenFOAM history; compare displacements, stresses, and temperature norms against CalculiX",
        "limitations": ["package generation does not execute Elmer", "Elmer mesh/material mapping must be verified independently"],
    }


def build_void_feedback_contract(*, history_package: dict, population_model: dict, stress_history: dict | None = None) -> dict:
    """Gate full void coupling inputs without promoting local seeded bubbles."""
    required = ("nucleation", "growth", "coalescence", "transport", "stress_feedback")
    checks = {name: name in population_model for name in required}
    checks["same_history_times"] = bool(history_package.get("time_s")) and list(population_model.get("time_s", history_package.get("time_s"))) == list(history_package.get("time_s"))
    checks["stress_history"] = stress_history is not None or bool(population_model.get("stress_feedback"))
    checks["calibrated_or_declared_virtual"] = population_model.get("data_status") in ("MEASURED", "VIRTUAL")
    return {
        "schema": "clawstack.void.feedback.contract.v1",
        "status": "INPUT_READY_NOT_SOLVED" if all(checks.values()) else "HOLD",
        "checks": checks,
        "mechanisms": list(required),
        "data_status": population_model.get("data_status", "UNKNOWN"),
        "limitations": [] if all(checks.values()) else ["void model is not yet a full nucleation/growth/coalescence/transport/stress-feedback calculation"],
    }


def convergence_report(reference: Sequence[float], candidate: Sequence[float], *, tolerance: float) -> dict:
    a, b = np.asarray(reference, dtype=float), np.asarray(candidate, dtype=float)
    if a.shape != b.shape or not a.size:
        raise ValueError("convergence arrays must have equal nonzero shape")
    rel = float(np.linalg.norm(a-b) / max(np.linalg.norm(a), 1e-300))
    return {"relative_l2": rel, "tolerance": float(tolerance), "pass": rel <= tolerance}


def validate_calibration(card: dict) -> dict:
    required = {"pvt", "cross_wlf", "cte"}
    present = {key for key in required if card.get(key)}
    measured = bool(card.get("metadata", {}).get("measured", False))
    pvt = card.get("pvt") or {}
    pvt_grid = pvt.get("density_kg_m3")
    pvt_positive = True
    if pvt_grid:
        pvt_positive = all(all(float(value) > 0.0 for value in row) for row in pvt_grid)
    cte = card.get("cte") or {}
    cte_valid = not cte or all(float(value) >= 0.0 for value in cte.values() if isinstance(value, (int, float)))
    cross = card.get("cross_wlf") or {}
    cross_valid = not cross or all(key in cross for key in ("n", "tau_star_pa", "d1_pa_s", "d2_k", "d3_k_pa", "a1", "a2_k"))
    quality = {"pvt_positive": pvt_positive, "cte_nonnegative": cte_valid, "cross_wlf_complete": cross_valid}
    ready = measured and present == required and all(quality.values())
    return {"required": sorted(required), "present": sorted(present), "complete": present == required,
            "measured": measured, "quality": quality,
            "status": "CALIBRATED_INPUT" if ready else "VIRTUAL_OR_INCOMPLETE"}


def build_contract(*, snapshot: dict, mapping: dict, calibration: dict, convergence: dict,
                   elmer_comparison: dict | None = None) -> dict:
    fields = snapshot["fields"]
    coupling_ready = bool(mapping.get("conservative")) and mapping.get("relative_error", 1.0) <= 1e-10
    calibration_report = validate_calibration(calibration)
    stages = {
        "openfoam_nonisothermal_compressible_fill": "FIELD_BUNDLE_VALIDATED",
        "same_mesh_time_T_p_alpha_U_rho": "PASS",
        "openfoam_to_calculix_conservative_transfer": "PASS" if coupling_ready else "HOLD",
        "cooling_solidification_shrinkage_warpage": "INPUT_READY" if coupling_ready else "HOLD",
        "elmer_independent_comparison": "RECORDED" if elmer_comparison else "PENDING",
        "void_nucleation_growth_coalescence_fill_coupling": "FIELD_CONTRACT_ONLY",
        "mesh_time_convergence": "PASS" if convergence.get("pass") else "HOLD",
        "measured_material_calibration": calibration_report["status"],
    }
    return {"schema": "clawstack.multiphysics.contract.v1", "status": "READY_FOR_SOLVER" if all(v in ("PASS", "FIELD_BUNDLE_VALIDATED", "INPUT_READY", "RECORDED", "CALIBRATED_INPUT", "FIELD_CONTRACT_ONLY") for v in stages.values()) else "HOLD", "cell_count": snapshot["cell_count"], "time_s": snapshot["time_s"], "fields": ["T", "p", "alpha", "U", "rho"], "stages": stages, "calibration": calibration_report, "convergence": convergence, "elmer_comparison": elmer_comparison, "limitations": ["A validated field bundle is not itself a solver result", "void coalescence requires a calibrated population model", "measured material data is required for engineering claims"]}


if __name__ == "__main__":
    raise SystemExit("Use the module from a case runner; no implicit solver execution is performed.")
