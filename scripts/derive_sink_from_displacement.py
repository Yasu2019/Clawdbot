"""Derive local sink-mark depth from a solved structural displacement field.

The calculation deliberately separates three different quantities:

* rigid motion and uniform isotropic shrinkage, removed by a least-squares
  proper similarity transform;
* low-wavelength surface depression, measured relative to a supplied local
  surface neighbourhood; and
* through-thickness change, measured only where an explicit outer/inner node
  pair is supplied.

The result is a field-derived screening quantity.  It is not promoted to a
calibrated product prediction without measured-material calibration evidence.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


SCHEMA = "clawstack.cae.sink.displacement_field.v1"
RESULT_CLASSIFICATION = "FIELD_DERIVED_UNCALIBRATED"
_UNIT_TO_M = {"m": 1.0, "mm": 1.0e-3, "um": 1.0e-6}
_PASS_WORDS = {"PASS", "PASSED", "COMPLETE", "COMPLETED", "CALIBRATED"}
_FRD_NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?")


def _vectors(name: str, values: Sequence[Sequence[float]], count: int | None = None) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or array.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N, 3)")
    if count is not None and len(array) != count:
        raise ValueError(f"{name} count differs from surface point count")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} contains non-finite values")
    return array


def _normalise_rows(normals: np.ndarray) -> np.ndarray:
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= np.finfo(float).tiny):
        raise ValueError("surface normals must be non-zero")
    return normals / lengths[:, None]


def _float_list(values: np.ndarray) -> list[float]:
    return [float(value) for value in values]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fit_proper_similarity(
    points: Sequence[Sequence[float]],
    deformed_points: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Fit ``y = scale * x @ rotation + translation`` without reflection.

    A similarity transform is used instead of a general affine fit because a
    free affine fit would also remove shear and anisotropic deformation that
    can be physically relevant to warpage and sink.  The fitted scalar scale
    is the global isotropic shrink/expansion component.
    """
    x = _vectors("points", points)
    y = _vectors("deformed_points", deformed_points, len(x))
    if len(x) < 3:
        raise ValueError("at least three points are required for similarity fitting")
    x_mean = np.mean(x, axis=0)
    y_mean = np.mean(y, axis=0)
    x_centered = x - x_mean
    y_centered = y - y_mean
    denominator = float(np.sum(x_centered * x_centered))
    if denominator <= np.finfo(float).tiny:
        raise ValueError("surface points have zero spatial extent")

    covariance = x_centered.T @ y_centered
    left, singular, right_t = np.linalg.svd(covariance)
    signs = np.ones(3, dtype=float)
    if float(np.linalg.det(left @ right_t)) < 0.0:
        signs[-1] = -1.0
    rotation = left @ np.diag(signs) @ right_t
    scale = float(np.dot(singular, signs) / denominator)
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("best-fit similarity has a non-positive scale")
    translation = y_mean - scale * (x_mean @ rotation)
    fitted = scale * (x @ rotation) + translation
    residual = y - fitted
    rms = float(np.sqrt(np.mean(np.sum(residual * residual, axis=1))))
    return {
        "scale": scale,
        "isotropic_strain": scale - 1.0,
        "rotation": rotation,
        "translation": translation,
        "fitted_points": fitted,
        "residual": residual,
        "rms_residual": rms,
    }


def _resolve_node(value: Any, id_to_index: Mapping[int, int], label: str) -> int:
    try:
        node_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} contains a non-integer node id: {value!r}") from exc
    if node_id not in id_to_index:
        raise ValueError(f"{label} references unknown node id {node_id}")
    return id_to_index[node_id]


def _normalise_neighbourhoods(
    neighborhoods: Mapping[Any, Sequence[Any]] | None,
    id_to_index: Mapping[int, int],
) -> dict[int, list[int]]:
    result: dict[int, list[int]] = {}
    for raw_center, raw_neighbors in (neighborhoods or {}).items():
        center = _resolve_node(raw_center, id_to_index, "neighborhood")
        if isinstance(raw_neighbors, (str, bytes)):
            raise ValueError("neighborhood values must be node-id sequences")
        resolved = []
        for raw_neighbor in raw_neighbors:
            neighbor = _resolve_node(raw_neighbor, id_to_index, "neighborhood")
            if neighbor != center and neighbor not in resolved:
                resolved.append(neighbor)
        result[center] = resolved
    return result


def _normalise_pairs(
    opposing_pairs: Sequence[Sequence[Any]] | None,
    id_to_index: Mapping[int, int],
) -> list[tuple[int, int]]:
    result = []
    seen = set()
    for raw_pair in opposing_pairs or ():
        if len(raw_pair) != 2:
            raise ValueError("every opposing pair must contain outer and inner node ids")
        outer = _resolve_node(raw_pair[0], id_to_index, "opposing pair")
        inner = _resolve_node(raw_pair[1], id_to_index, "opposing pair")
        if outer == inner:
            raise ValueError("outer and inner nodes must differ")
        pair = (outer, inner)
        if pair not in seen:
            seen.add(pair)
            result.append(pair)
    return result


def derive_sink_field(
    surface_points: Sequence[Sequence[float]],
    surface_normals: Sequence[Sequence[float]],
    displacement: Sequence[Sequence[float]],
    *,
    node_ids: Sequence[int] | None = None,
    neighborhoods: Mapping[Any, Sequence[Any]] | None = None,
    opposing_pairs: Sequence[Sequence[Any]] | None = None,
    length_unit: str = "m",
    display_scale: float = 1.0,
    measured_calibration: bool = False,
    minimum_local_support: int = 3,
    normal_alignment_min: float = 0.5,
) -> dict[str, Any]:
    """Derive a local surface-depression field and optional thickness change.

    ``surface_normals`` must point out of the polymer.  Positive sink depth is
    inward, i.e. opposite the outward normal.  ``display_scale`` affects only
    explicitly labelled visualization values; all physical metrics are
    invariant to it.
    """
    if length_unit not in _UNIT_TO_M:
        raise ValueError(f"unsupported length unit {length_unit!r}")
    if not math.isfinite(display_scale) or display_scale <= 0.0:
        raise ValueError("display_scale must be finite and positive")
    if minimum_local_support < 1:
        raise ValueError("minimum_local_support must be at least one")
    if not -1.0 <= normal_alignment_min <= 1.0:
        raise ValueError("normal_alignment_min must lie in [-1, 1]")

    unit_to_m = _UNIT_TO_M[length_unit]
    points_input = _vectors("surface_points", surface_points)
    normals_reference = _normalise_rows(_vectors("surface_normals", surface_normals, len(points_input)))
    displacement_input = _vectors("displacement", displacement, len(points_input))
    if node_ids is None:
        ids = list(range(len(points_input)))
    else:
        ids = [int(value) for value in node_ids]
        if len(ids) != len(points_input):
            raise ValueError("node_ids count differs from surface point count")
        if len(set(ids)) != len(ids):
            raise ValueError("node_ids must be unique")
    id_to_index = {node_id: index for index, node_id in enumerate(ids)}
    local_map = _normalise_neighbourhoods(neighborhoods, id_to_index)
    pair_map = _normalise_pairs(opposing_pairs, id_to_index)

    points_m = points_input * unit_to_m
    displacement_m = displacement_input * unit_to_m
    deformed_m = points_m + displacement_m
    fit = fit_proper_similarity(points_m, deformed_m)
    rotation = fit["rotation"]
    residual_m = fit["residual"]
    normals_fitted = _normalise_rows(normals_reference @ rotation)
    residual_normal_m = np.sum(residual_m * normals_fitted, axis=1)

    surface_records: list[dict[str, Any]] = []
    valid_sink_m: list[float] = []
    for index, node_id in enumerate(ids):
        support = []
        for neighbor in local_map.get(index, []):
            alignment = float(np.dot(normals_fitted[index], normals_fitted[neighbor]))
            if alignment >= normal_alignment_min:
                support.append(neighbor)
        if len(support) >= minimum_local_support:
            # Project all neighbouring residual vectors onto the centre normal;
            # the median is a robust local baseline and excludes the centre.
            local_values = residual_m[support] @ normals_fitted[index]
            local_reference_m = float(np.median(local_values))
            sink_m = max(0.0, local_reference_m - float(residual_normal_m[index]))
            valid_sink_m.append(sink_m)
            context_status = "VALID_LOCAL_NEIGHBORHOOD"
        else:
            local_reference_m = None
            sink_m = None
            context_status = "HOLD_INSUFFICIENT_LOCAL_SUPPORT"
        surface_records.append(
            {
                "node_id": node_id,
                "context_status": context_status,
                "local_support_count": len(support),
                "residual_displacement_m": _float_list(residual_m[index]),
                "residual_normal_displacement_m": float(residual_normal_m[index]),
                "local_reference_normal_displacement_m": local_reference_m,
                "sink_depth_m": sink_m,
                "sink_depth_mm": None if sink_m is None else sink_m * 1.0e3,
                "sink_depth_um": None if sink_m is None else sink_m * 1.0e6,
                "display_sink_depth_m": None if sink_m is None else sink_m * display_scale,
            }
        )

    pair_records: list[dict[str, Any]] = []
    valid_pair_loss_m: list[float] = []
    for outer, inner in pair_map:
        reference_vector = points_m[outer] - points_m[inner]
        reference_thickness_m = float(np.linalg.norm(reference_vector))
        if reference_thickness_m <= np.finfo(float).tiny:
            raise ValueError(f"opposing pair {ids[outer]}/{ids[inner]} has zero reference thickness")
        reference_axis = reference_vector / reference_thickness_m
        orientation_outer = float(np.dot(normals_reference[outer], reference_axis))
        orientation_inner = float(np.dot(normals_reference[inner], -reference_axis))
        orientation_valid = (
            orientation_outer >= normal_alignment_min
            and orientation_inner >= normal_alignment_min
        )
        fitted_axis = reference_axis @ rotation
        actual_thickness_m = float(np.dot(deformed_m[outer] - deformed_m[inner], fitted_axis))
        expected_uniform_thickness_m = float(fit["scale"]) * reference_thickness_m
        localized_thickness_change_m = actual_thickness_m - expected_uniform_thickness_m
        excess_thickness_loss_m = max(0.0, -localized_thickness_change_m)
        if orientation_valid and actual_thickness_m > 0.0:
            valid_pair_loss_m.append(excess_thickness_loss_m)
            pair_status = "VALID_OPPOSING_PAIR"
        else:
            pair_status = "HOLD_INVALID_PAIR_ORIENTATION"
        pair_records.append(
            {
                "outer_node_id": ids[outer],
                "inner_node_id": ids[inner],
                "status": pair_status,
                "outer_normal_alignment": orientation_outer,
                "inner_normal_alignment": orientation_inner,
                "reference_thickness_m": reference_thickness_m,
                "actual_projected_thickness_m": actual_thickness_m,
                "total_thickness_change_m": actual_thickness_m - reference_thickness_m,
                "expected_uniform_thickness_m": expected_uniform_thickness_m,
                "localized_thickness_change_m": localized_thickness_change_m,
                "excess_thickness_loss_m": excess_thickness_loss_m,
                "excess_thickness_loss_mm": excess_thickness_loss_m * 1.0e3,
                "pair_equivalent_depression_per_face_m": 0.5 * excess_thickness_loss_m,
            }
        )

    local_context_supplied = bool(local_map) or bool(pair_map)
    local_context_valid = bool(valid_sink_m) or bool(valid_pair_loss_m)
    hold_reasons = []
    if not local_context_supplied:
        hold_reasons.append("local_neighborhood_or_inner_outer_mapping_missing")
    elif not local_context_valid:
        hold_reasons.append("local_neighborhood_or_inner_outer_mapping_invalid")
    if not measured_calibration:
        hold_reasons.append("measured_material_and_process_calibration_missing")
    status = "PASS_FIELD_DERIVED" if not hold_reasons else "HOLD"

    max_sink_m = max(valid_sink_m, default=0.0)
    mean_sink_m = float(np.mean(valid_sink_m)) if valid_sink_m else 0.0
    max_pair_loss_m = max(valid_pair_loss_m, default=0.0)
    residual_norms_m = np.linalg.norm(residual_m, axis=1)
    return {
        "schema": SCHEMA,
        "status": status,
        "result_classification": RESULT_CLASSIFICATION,
        "engineering_claim": "NONE" if hold_reasons else "FIELD_DERIVED_ONLY",
        "coordinate_and_displacement_unit": length_unit,
        "sign_convention": "positive sink depth is inward, opposite the supplied outward surface normal",
        "decomposition": {
            "model": "proper_similarity_plus_local_normal_residual",
            "rationale": "remove rigid motion and isotropic shrink, but retain physical shear/anisotropy",
            "uniform_scale": float(fit["scale"]),
            "uniform_isotropic_strain": float(fit["isotropic_strain"]),
            "rotation_matrix_row_vector_convention": [
                _float_list(row) for row in fit["rotation"]
            ],
            "translation_m": _float_list(fit["translation"]),
            "rms_residual_m": float(fit["rms_residual"]),
            "max_residual_norm_m": float(np.max(residual_norms_m)),
        },
        "surface_depression": {
            "method": "local_median_baseline_minus_center_normal_residual",
            "valid_node_count": len(valid_sink_m),
            "total_node_count": len(ids),
            "max_sink_depth_m": max_sink_m,
            "max_sink_depth_mm": max_sink_m * 1.0e3,
            "max_sink_depth_um": max_sink_m * 1.0e6,
            "mean_sink_depth_m": mean_sink_m,
            "field": surface_records,
        },
        "thickness_change": {
            "method": "explicit_outer_inner_pair_projected_on_fitted_reference_axis",
            "valid_pair_count": len(valid_pair_loss_m),
            "total_pair_count": len(pair_map),
            "max_excess_thickness_loss_m": max_pair_loss_m,
            "max_excess_thickness_loss_mm": max_pair_loss_m * 1.0e3,
            "field": pair_records,
        },
        "visualization": {
            "exaggeration_factor": float(display_scale),
            "quantity": "display_sink_depth_m = physical_sink_depth_m * exaggeration_factor",
            "physical_metrics_scaled": False,
            "warning": "display exaggeration is not a physical displacement or predicted sink depth",
        },
        "production_gate": {
            "status": "PASS" if not hold_reasons else "HOLD",
            "hold_reasons": hold_reasons,
            "measured_calibration_supplied": bool(measured_calibration),
            "local_context_supplied": local_context_supplied,
            "local_context_valid": local_context_valid,
        },
        "limitations": [
            "FIELD_DERIVED_UNCALIBRATED is a numerical screening classification, not a product-quality claim.",
            "Surface sink needs a topology-aware local neighbourhood; pair data alone reports thickness loss, not which face visibly sinks.",
            "Inner/outer pairing must be geometry-derived and orientation-checked for an arbitrary 3D model.",
            "A 50x or other display factor changes visualization only and never changes physical field values.",
        ],
    }


def load_surface_csv(path: Path) -> dict[str, Any]:
    """Load node id, coordinates, outward normals, and optional displacement."""
    required = ("node_id", "x", "y", "z", "nx", "ny", "nz")
    nodes: list[int] = []
    points: list[list[float]] = []
    normals: list[list[float]] = []
    inline_displacement: list[list[float]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in required if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"surface CSV missing columns: {missing}")
        has_displacement = all(name in (reader.fieldnames or []) for name in ("ux", "uy", "uz"))
        for row in reader:
            nodes.append(int(row["node_id"]))
            points.append([float(row[name]) for name in ("x", "y", "z")])
            normals.append([float(row[name]) for name in ("nx", "ny", "nz")])
            if has_displacement:
                inline_displacement.append([float(row[name]) for name in ("ux", "uy", "uz")])
    if not nodes:
        raise ValueError("surface CSV has no data rows")
    return {
        "node_ids": nodes,
        "points": points,
        "normals": normals,
        "inline_displacement": inline_displacement if inline_displacement else None,
    }


def load_displacement_csv(path: Path) -> dict[int, tuple[float, float, float]]:
    required = ("node_id", "ux", "uy", "uz")
    result: dict[int, tuple[float, float, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name in required if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"displacement CSV missing columns: {missing}")
        for row in reader:
            node_id = int(row["node_id"])
            if node_id in result:
                raise ValueError(f"duplicate displacement node id {node_id}")
            result[node_id] = tuple(float(row[name]) for name in ("ux", "uy", "uz"))
    if not result:
        raise ValueError("displacement CSV has no data rows")
    return result


def load_ccx_frd_displacement(path: Path) -> dict[int, tuple[float, float, float]]:
    """Load the last ASCII CalculiX FRD ``DISP`` result block.

    Binary FRD and non-standard field encodings are rejected rather than
    silently interpreted.  The surface coordinates/normals remain a separate,
    explicit input so deformed-vs-reference coordinate semantics cannot drift.
    """
    blocks: list[dict[int, tuple[float, float, float]]] = []
    current: dict[int, tuple[float, float, float]] | None = None
    reading_values = False
    for raw_line in path.read_text(encoding="latin-1").splitlines():
        upper = raw_line.upper()
        if re.search(r"\bDISP\b", upper):
            current = {}
            reading_values = False
            continue
        if current is None:
            continue
        marker = raw_line.lstrip()
        if marker.startswith("-5"):
            reading_values = True
            continue
        if reading_values and marker.startswith("-1"):
            numbers = _FRD_NUMBER.findall(raw_line.replace("D", "E").replace("d", "e"))
            if len(numbers) < 5:
                raise ValueError(f"malformed FRD displacement record: {raw_line!r}")
            node_id = int(numbers[1])
            current[node_id] = tuple(float(value.replace("D", "E").replace("d", "e")) for value in numbers[2:5])
            continue
        if reading_values and marker.startswith("-3"):
            if current:
                blocks.append(current)
            current = None
            reading_values = False
    if current:
        blocks.append(current)
    if not blocks:
        raise ValueError("no ASCII DISP result block found in CalculiX FRD")
    return blocks[-1]


def _load_neighborhoods(path: Path | None) -> Mapping[Any, Sequence[Any]] | None:
    if path is None:
        return None
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(value, Mapping) and "neighborhoods" in value:
        value = value["neighborhoods"]
    if not isinstance(value, Mapping):
        raise ValueError("neighborhood JSON must be an object keyed by node id")
    return value


def _load_pairs(path: Path | None) -> list[tuple[int, int]] | None:
    if path is None:
        return None
    result = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"outer_node_id", "inner_node_id"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("pairs CSV needs outer_node_id and inner_node_id columns")
        for row in reader:
            result.append((int(row["outer_node_id"]), int(row["inner_node_id"])))
    return result


def _calibration_pass(path: Path | None) -> tuple[bool, dict[str, Any] | None]:
    if path is None:
        return False, None
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, Mapping):
        raise ValueError("calibration JSON must be an object")
    is_measured = str(value.get("kind", "")).strip().lower() == "measured"
    status = str(value.get("calibration_status", value.get("status", ""))).strip().upper()
    passed = is_measured and status in _PASS_WORDS
    return passed, {"path": str(path.resolve()), "sha256": _sha256(path), "accepted": passed}


def _write_field_csv(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "node_id", "context_status", "local_support_count",
        "residual_normal_displacement_m", "local_reference_normal_displacement_m",
        "sink_depth_m", "sink_depth_mm", "sink_depth_um", "display_sink_depth_m",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in report["surface_depression"]["field"]:
            writer.writerow({name: record.get(name) for name in columns})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface-csv", type=Path, required=True)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--displacement-csv", type=Path)
    source.add_argument("--frd", type=Path, help="CalculiX ASCII FRD; last DISP block is used")
    parser.add_argument("--neighborhoods-json", type=Path)
    parser.add_argument("--pairs-csv", type=Path)
    parser.add_argument("--measured-calibration-json", type=Path)
    parser.add_argument("--length-unit", choices=sorted(_UNIT_TO_M), default="mm")
    parser.add_argument("--display-scale", type=float, default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--field-csv", type=Path)
    args = parser.parse_args()

    try:
        surface = load_surface_csv(args.surface_csv)
        if args.displacement_csv:
            displacement_by_node = load_displacement_csv(args.displacement_csv)
        elif args.frd:
            displacement_by_node = load_ccx_frd_displacement(args.frd)
        elif surface["inline_displacement"] is not None:
            displacement_by_node = dict(zip(surface["node_ids"], surface["inline_displacement"]))
        else:
            raise ValueError("provide --displacement-csv/--frd or ux,uy,uz in surface CSV")
        missing = [node_id for node_id in surface["node_ids"] if node_id not in displacement_by_node]
        if missing:
            raise ValueError(f"displacement is missing {len(missing)} surface nodes; first={missing[:5]}")
        calibrated, calibration_evidence = _calibration_pass(args.measured_calibration_json)
        report = derive_sink_field(
            surface["points"],
            surface["normals"],
            [displacement_by_node[node_id] for node_id in surface["node_ids"]],
            node_ids=surface["node_ids"],
            neighborhoods=_load_neighborhoods(args.neighborhoods_json),
            opposing_pairs=_load_pairs(args.pairs_csv),
            length_unit=args.length_unit,
            display_scale=args.display_scale,
            measured_calibration=calibrated,
        )
        report["inputs"] = {
            "surface_csv": {"path": str(args.surface_csv.resolve()), "sha256": _sha256(args.surface_csv)},
            "displacement_source": str((args.displacement_csv or args.frd or args.surface_csv).resolve()),
            "calibration_evidence": calibration_evidence,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.field_csv:
            _write_field_csv(args.field_csv, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "PASS_FIELD_DERIVED" else 2
    except (OSError, UnicodeError, csv.Error, json.JSONDecodeError, ValueError) as exc:
        failure = {
            "schema": SCHEMA,
            "status": "HOLD",
            "result_classification": RESULT_CLASSIFICATION,
            "engineering_claim": "NONE",
            "failed_checks": [f"input_or_derivation_error:{type(exc).__name__}:{exc}"],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
