# -*- coding: utf-8 -*-
"""Leakage-safe nodal warpage comparison for Moldflow vs CalculiX."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


Vector = tuple[float, float, float]


def _read_vectors(path: Path, columns: tuple[str, str, str]) -> dict[int, Vector]:
    result: dict[int, Vector] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"NodeID", *columns}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
        for row in reader:
            node = int(row["NodeID"])
            if node in result:
                raise ValueError(f"duplicate NodeID {node} in {path.name}")
            vector = tuple(float(row[name]) for name in columns)
            if not all(math.isfinite(value) for value in vector):
                raise ValueError(f"non-finite vector at NodeID {node}")
            result[node] = vector  # type: ignore[assignment]
    if not result:
        raise ValueError(f"{path.name} is empty")
    return result


def _magnitude(vector: Vector) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    dl = [value - mean_l for value in left]
    dr = [value - mean_r for value in right]
    denom = math.sqrt(sum(value * value for value in dl) * sum(value * value for value in dr))
    if denom == 0:
        return 1.0 if left == right else None
    return sum(a * b for a, b in zip(dl, dr)) / denom


def score_warpage(
    reference: dict[int, Vector],
    prediction: dict[int, Vector],
    provenance: dict[str, Any],
    *,
    coverage_min: float = 0.99,
    vector_nrmse_max: float = 0.15,
    peak_relative_error_max: float = 0.20,
) -> dict[str, Any]:
    common = sorted(set(reference) & set(prediction))
    coverage = len(common) / len(reference)
    if not common:
        raise ValueError("reference and prediction have no common NodeID")

    squared_error = 0.0
    squared_reference = 0.0
    components_ref = [[], [], []]
    components_pred = [[], [], []]
    for node in common:
        ref = reference[node]
        pred = prediction[node]
        squared_error += sum((pred[i] - ref[i]) ** 2 for i in range(3))
        squared_reference += sum(ref[i] ** 2 for i in range(3))
        for axis in range(3):
            components_ref[axis].append(ref[axis])
            components_pred[axis].append(pred[axis])
    rmse_mm = math.sqrt(squared_error / len(common))
    reference_rms_mm = math.sqrt(squared_reference / len(common))
    vector_nrmse = rmse_mm / reference_rms_mm if reference_rms_mm > 0 else math.inf
    ref_peak = max(_magnitude(reference[node]) for node in common)
    pred_peak = max(_magnitude(prediction[node]) for node in common)
    peak_relative_error = abs(pred_peak - ref_peak) / ref_peak if ref_peak > 0 else math.inf

    load_source = str(provenance.get("load_source") or "")
    independent = load_source == "INDEPENDENT_OPENFOAM_HISTORY"
    scale_fit = bool(provenance.get("global_scale_fit", False))
    source_run_id = str(provenance.get("source_run_id") or "")
    provenance_pass = independent and bool(source_run_id) and not scale_fit
    gates = {
        "coverage": coverage >= coverage_min,
        "vector_nrmse": vector_nrmse <= vector_nrmse_max,
        "peak_relative_error": peak_relative_error <= peak_relative_error_max,
        "independent_load_provenance": provenance_pass,
    }
    return {
        "label": "PROXY_OK" if all(gates.values()) else "PROXY_GAP",
        "never_claim": "MOLDFLOW_EQUIVALENT",
        "units": "mm",
        "reference_nodes": len(reference),
        "prediction_nodes": len(prediction),
        "common_nodes": len(common),
        "coverage": coverage,
        "rmse_mm": rmse_mm,
        "reference_rms_mm": reference_rms_mm,
        "vector_nrmse": vector_nrmse,
        "reference_peak_mm": ref_peak,
        "prediction_peak_mm": pred_peak,
        "peak_relative_error": peak_relative_error,
        "component_correlation": {
            axis: _correlation(components_ref[index], components_pred[index])
            for index, axis in enumerate(("X", "Y", "Z"))
        },
        "gates": gates,
        "thresholds": {
            "coverage_min": coverage_min,
            "vector_nrmse_max": vector_nrmse_max,
            "peak_relative_error_max": peak_relative_error_max,
        },
        "provenance": provenance,
        "forbidden_operations": ["axis_soft_match", "global_scale_fit_on_validation_case"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--prediction-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = _read_vectors(args.reference, ("vx", "vy", "vz"))
    prediction = _read_vectors(args.prediction, ("ux_mm", "uy_mm", "uz_mm"))
    provenance = json.loads(args.prediction_manifest.read_text(encoding="utf-8"))
    result = score_warpage(reference, prediction, provenance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"label": result["label"], "coverage": result["coverage"], "vector_nrmse": result["vector_nrmse"], "peak_relative_error": result["peak_relative_error"]}))
    return 0 if result["label"] == "PROXY_OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
