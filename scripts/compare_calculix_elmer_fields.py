"""Compare CalculiX and Elmer fields on one reference mesh, fail closed.

This is an independent-solver *numerical* comparison gate.  It does not turn
uncalibrated material data into a validated product prediction.  Both inputs
must expose displacement, temperature, and von-Mises stress in VTU point data.
Node ordering may differ; a one-to-one geometric match is constructed from
reference coordinates before any field norm is calculated.
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
import itertools
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


FIELD_ALIASES = {
    "displacement": (
        "displacement",
        "Displacement",
        "DISP",
        "Displacement Vector",
    ),
    "temperature": ("temperature", "Temperature", "TEMP", "T"),
    "von_mises_stress": (
        "von_mises_stress",
        "von Mises stress",
        "vonMises",
        "VonMises",
        "Mises",
        "S_Mises",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_array(values: Any, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain finite values")
    return array


def _field(point_data: dict[str, Any], logical_name: str) -> tuple[str, np.ndarray]:
    for alias in FIELD_ALIASES[logical_name]:
        if alias in point_data:
            values = _finite_array(point_data[alias], name=logical_name)
            if logical_name == "displacement":
                if values.ndim != 2 or values.shape[1] < 3:
                    raise ValueError("displacement must be an N x 3 point field")
                values = values[:, :3]
            else:
                values = values.reshape(-1)
            return alias, values
    raise ValueError(
        f"required point field {logical_name!r} is missing; "
        f"accepted aliases={FIELD_ALIASES[logical_name]}"
    )


def load_vtu_fields(path: Path, *, coordinates_deformed: bool = False) -> dict[str, Any]:
    """Load reference coordinates and the three required nodal fields."""

    try:
        import meshio
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("meshio is required to read VTU evidence") from exc

    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(path)
    mesh = meshio.read(path)
    points = _finite_array(mesh.points, name="points")
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError("VTU points must be N x 3")
    points = points[:, :3]

    displacement_name, displacement = _field(mesh.point_data, "displacement")
    temperature_name, temperature = _field(mesh.point_data, "temperature")
    stress_name, stress = _field(mesh.point_data, "von_mises_stress")
    point_count = len(points)
    for name, values in (
        ("displacement", displacement),
        ("temperature", temperature),
        ("von_mises_stress", stress),
    ):
        if len(values) != point_count:
            raise ValueError(f"{name} point count does not match VTU points")

    reference_points = points - displacement if coordinates_deformed else points.copy()
    return {
        "path": str(path.resolve()),
        "sha256": _sha256(path),
        "point_count": point_count,
        "reference_points": reference_points,
        "displacement": displacement,
        "temperature": temperature,
        "von_mises_stress": stress,
        "source_field_names": {
            "displacement": displacement_name,
            "temperature": temperature_name,
            "von_mises_stress": stress_name,
        },
        "coordinates_deformed": bool(coordinates_deformed),
    }


def _one_to_one_match(
    reference: np.ndarray,
    candidate: np.ndarray,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> tuple[np.ndarray, dict[str, float]]:
    if reference.shape != candidate.shape:
        raise ValueError(
            f"point shapes differ: CalculiX={reference.shape}, Elmer={candidate.shape}"
        )
    if absolute_tolerance < 0.0 or relative_tolerance < 0.0:
        raise ValueError("coordinate tolerances must be non-negative")

    span = np.ptp(reference, axis=0)
    diagonal = float(np.linalg.norm(span))
    tolerance = max(float(absolute_tolerance), float(relative_tolerance) * diagonal)
    if tolerance <= 0.0:
        tolerance = np.finfo(float).eps

    # A tolerance-sized spatial hash is O(N) for a regular FE mesh and avoids
    # the prohibitive O(N**2) distance matrix that large product meshes would
    # otherwise require.  Degenerate/ambiguous coincident nodes fail closed.
    buckets: dict[tuple[int, int, int], list[int]] = {}
    for candidate_id, point in enumerate(candidate):
        key = tuple(int(math.floor(value / tolerance)) for value in point)
        buckets.setdefault(key, []).append(candidate_id)
    mapping = np.full(len(reference), -1, dtype=np.int64)
    distances = np.empty(len(reference), dtype=float)
    available = np.ones(len(candidate), dtype=bool)
    for index, point in enumerate(reference):
        base_key = tuple(int(math.floor(value / tolerance)) for value in point)
        candidate_ids: list[int] = []
        for offset in itertools.product((-1, 0, 1), repeat=3):
            neighbour_key = tuple(base_key[axis] + offset[axis] for axis in range(3))
            candidate_ids.extend(
                candidate_id
                for candidate_id in buckets.get(neighbour_key, ())
                if available[candidate_id]
            )
        if not candidate_ids:
            raise ValueError(
                f"no one-to-one Elmer node within tolerance for CalculiX node {index}: "
                f"no candidate bucket, tolerance={tolerance:.9g}"
            )
        candidate_array = np.asarray(candidate_ids, dtype=np.int64)
        local_distance = np.linalg.norm(candidate[candidate_array] - point, axis=1)
        nearest_local = int(np.argmin(local_distance))
        nearest_id = int(candidate_array[nearest_local])
        distance = float(local_distance[nearest_local])
        if distance > tolerance:
            raise ValueError(
                f"no one-to-one Elmer node within tolerance for CalculiX node {index}: "
                f"distance={distance:.9g}, tolerance={tolerance:.9g}"
            )
        mapping[index] = nearest_id
        distances[index] = distance
        available[nearest_id] = False

    if np.any(mapping < 0) or len(np.unique(mapping)) != len(mapping):
        raise ValueError("node mapping is not one-to-one")
    return mapping, {
        "geometry_diagonal": diagonal,
        "coordinate_tolerance": tolerance,
        "maximum_match_distance": float(np.max(distances, initial=0.0)),
        "rms_match_distance": float(np.sqrt(np.mean(distances * distances))),
    }


def _metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    delta = candidate - reference
    ref_norm = float(np.linalg.norm(reference.reshape(-1)))
    delta_norm = float(np.linalg.norm(delta.reshape(-1)))
    scale = max(ref_norm, float(np.linalg.norm(candidate.reshape(-1))), 1.0e-30)
    return {
        "reference_l2": ref_norm,
        "candidate_l2": float(np.linalg.norm(candidate.reshape(-1))),
        "absolute_l2_error": delta_norm,
        "relative_l2_error": delta_norm / scale,
        "absolute_linf_error": float(np.max(np.abs(delta), initial=0.0)),
        "reference_min": float(np.min(reference)),
        "reference_max": float(np.max(reference)),
        "candidate_min": float(np.min(candidate)),
        "candidate_max": float(np.max(candidate)),
    }


def compare_fields(
    calculix: dict[str, Any],
    elmer: dict[str, Any],
    *,
    identity: dict[str, str],
    displacement_relative_tolerance: float = 0.10,
    temperature_relative_tolerance: float = 0.05,
    stress_relative_tolerance: float = 0.20,
    coordinate_absolute_tolerance: float = 1.0e-10,
    coordinate_relative_tolerance: float = 1.0e-8,
    calibrated: bool = False,
) -> dict[str, Any]:
    """Compare mapped fields and return a strict evidence manifest."""

    required_identity = ("geometry_sha256", "mesh_sha256", "history_id")
    missing_identity = [key for key in required_identity if not str(identity.get(key, "")).strip()]
    if missing_identity:
        raise ValueError(f"missing identity values: {missing_identity}")
    for key in ("geometry_sha256", "mesh_sha256"):
        value = str(identity[key])
        if len(value) != 64 or any(character not in "0123456789abcdefABCDEF" for character in value):
            raise ValueError(f"{key} must be a SHA-256 hexadecimal digest")
    tolerances = {
        "displacement": float(displacement_relative_tolerance),
        "temperature": float(temperature_relative_tolerance),
        "von_mises_stress": float(stress_relative_tolerance),
    }
    if any(not math.isfinite(value) or value < 0.0 for value in tolerances.values()):
        raise ValueError("field tolerances must be finite and non-negative")

    mapping, mapping_metrics = _one_to_one_match(
        calculix["reference_points"],
        elmer["reference_points"],
        absolute_tolerance=coordinate_absolute_tolerance,
        relative_tolerance=coordinate_relative_tolerance,
    )
    comparisons: dict[str, Any] = {}
    failed_checks: list[str] = []
    for field_name, tolerance in tolerances.items():
        reference = np.asarray(calculix[field_name], dtype=float)
        candidate = np.asarray(elmer[field_name], dtype=float)[mapping]
        field_metrics = _metrics(reference, candidate)
        passed = field_metrics["relative_l2_error"] <= tolerance
        field_metrics.update(relative_tolerance=tolerance, status="PASS" if passed else "HOLD")
        comparisons[field_name] = field_metrics
        if not passed:
            failed_checks.append(f"field.{field_name}.relative_l2_error")

    numerical_pass = not failed_checks
    if numerical_pass and calibrated:
        status = "CROSS_SOLVER_NUMERICAL_PASS_CALIBRATED_INPUT"
        classification = "CALIBRATED_NUMERICAL_COMPARISON"
    elif numerical_pass:
        status = "CROSS_SOLVER_NUMERICAL_PASS_UNCALIBRATED"
        classification = "UNCALIBRATED_SCREENING"
    else:
        status = "HOLD"
        classification = "NUMERICAL_COMPARISON_FAILED"

    return {
        "schema": "clawstack.calculix-elmer.field-comparison.v1",
        "status": status,
        "classification": classification,
        **{key: identity[key] for key in required_identity},
        "same_geometry_mesh_history": True,
        "calibrated_material_input": bool(calibrated),
        "calculix": {
            key: calculix[key]
            for key in ("path", "sha256", "point_count", "source_field_names", "coordinates_deformed")
        },
        "elmer": {
            key: elmer[key]
            for key in ("path", "sha256", "point_count", "source_field_names", "coordinates_deformed")
        },
        "mapping": {"method": "one_to_one_reference_coordinate", **mapping_metrics},
        "fields": comparisons,
        "failed_checks": failed_checks,
        "limitations": [
            "This proves field-level agreement between two numerical solvers, not agreement with experiment.",
            "The comparison requires both VTUs to use the same physical units and reference geometry.",
            "Virtual or generic material inputs remain screening-only until measured calibration is supplied.",
        ],
    }


def compare_vtu_files(
    calculix_vtu: Path,
    elmer_vtu: Path,
    *,
    identity: dict[str, str],
    calculix_coordinates_deformed: bool = False,
    elmer_coordinates_deformed: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    calculix = load_vtu_fields(
        calculix_vtu, coordinates_deformed=calculix_coordinates_deformed
    )
    elmer = load_vtu_fields(elmer_vtu, coordinates_deformed=elmer_coordinates_deformed)
    return compare_fields(calculix, elmer, identity=identity, **kwargs)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calculix-vtu", type=Path, required=True)
    parser.add_argument("--elmer-vtu", type=Path, required=True)
    parser.add_argument("--geometry-sha256", required=True)
    parser.add_argument("--mesh-sha256", required=True)
    parser.add_argument("--history-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calculix-coordinates-deformed", action="store_true")
    parser.add_argument("--elmer-coordinates-deformed", action="store_true")
    parser.add_argument("--displacement-relative-tolerance", type=float, default=0.10)
    parser.add_argument("--temperature-relative-tolerance", type=float, default=0.05)
    parser.add_argument("--stress-relative-tolerance", type=float, default=0.20)
    parser.add_argument("--coordinate-absolute-tolerance", type=float, default=1.0e-10)
    parser.add_argument("--coordinate-relative-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--calibrated", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    report = compare_vtu_files(
        args.calculix_vtu,
        args.elmer_vtu,
        identity={
            "geometry_sha256": args.geometry_sha256,
            "mesh_sha256": args.mesh_sha256,
            "history_id": args.history_id,
        },
        calculix_coordinates_deformed=args.calculix_coordinates_deformed,
        elmer_coordinates_deformed=args.elmer_coordinates_deformed,
        displacement_relative_tolerance=args.displacement_relative_tolerance,
        temperature_relative_tolerance=args.temperature_relative_tolerance,
        stress_relative_tolerance=args.stress_relative_tolerance,
        coordinate_absolute_tolerance=args.coordinate_absolute_tolerance,
        coordinate_relative_tolerance=args.coordinate_relative_tolerance,
        calibrated=args.calibrated,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("CROSS_SOLVER_NUMERICAL_PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
