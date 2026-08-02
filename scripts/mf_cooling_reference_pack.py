# -*- coding: utf-8 -*-
"""Build unit-aware Moldflow cooling targets for OpenFOAM calibration."""
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DIRECT_FIELDS = (
    "temperature_nodal",
    "temperature_part",
    "average_temperature_part",
    "temperature_mold",
    "time_to_ejection_temp",
    "time_to_reach_ejection_temperature_part",
    "frozen_layer_eof",
    "frozen_layer_fraction_last",
    "circuit_coolant_temperature",
    "circuit_metal_temperature",
    "circuit_pressure",
)
COMPARISON_ONLY_FIELDS = (
    "volumetric_shrinkage_ejection",
    "sink_marks_index",
    "circuit_flow_rate",
)
EXCLUDED_FIELDS = {
    "temperature_difference_from_mold_walls": (
        "Observed median is approximately -273.15 in the exported source. "
        "Temperature differences must not receive an absolute-temperature offset."
    )
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("quantile requires values")
    index = min(len(values) - 1, max(0, round((len(values) - 1) * fraction)))
    return values[index]


def _stats(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("field contains no finite values")
    return {
        "min": ordered[0],
        "p05": _quantile(ordered, 0.05),
        "median": _quantile(ordered, 0.50),
        "mean": sum(ordered) / len(ordered),
        "p95": _quantile(ordered, 0.95),
        "max": ordered[-1],
    }


def _converter(source_unit: str, output_unit: str) -> Callable[[float], float]:
    if source_unit == output_unit:
        return float
    if source_unit == "degC" and output_unit == "K":
        return lambda value: float(value) + 273.15
    if source_unit == "MPa" and output_unit == "Pa":
        return lambda value: float(value) * 1.0e6
    raise ValueError(f"unsupported verified conversion: {source_unit} -> {output_unit}")


def _read_scalar_csv(path: Path) -> tuple[list[float], list[float]]:
    values: list[float] = []
    independent: list[float] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "value" not in set(reader.fieldnames or []):
            raise ValueError(f"{path.name} is not a scalar result")
        for row in reader:
            value = float(row["value"])
            if math.isfinite(value) and abs(value) < 1.0e30:
                values.append(value)
            raw_indp = row.get("indp")
            if raw_indp not in (None, ""):
                try:
                    indp = float(raw_indp)
                except ValueError:
                    continue
                if math.isfinite(indp):
                    independent.append(indp)
    return values, independent


def _field_record(source: Path, prefix: str, slug: str, meta: dict[str, Any], direct: bool) -> dict[str, Any]:
    path = source / f"{prefix}_{slug}.csv"
    if not path.is_file():
        raise FileNotFoundError(path)
    values, independent = _read_scalar_csv(path)
    source_unit = str(meta.get("source_unit") or "UNVERIFIED")
    output_unit = str(meta.get("output_unit") or "SOURCE_RAW")
    verified = bool(meta.get("unit_verified"))
    if direct and not verified:
        raise ValueError(f"direct field {slug} has unverified units")
    record: dict[str, Any] = {
        "source": str(path.resolve()),
        "sha256": _sha256(path),
        "association": list(meta.get("associations") or []),
        "rows": len(values),
        "source_unit": source_unit,
        "output_unit": output_unit,
        "unit_verified": verified,
        "solver_role": "CALIBRATION_TARGET" if direct else "COMPARISON_ONLY_SOURCE_RAW",
        "raw_stats": _stats(values),
        "independent_values": sorted(set(independent)),
    }
    if direct:
        convert = _converter(source_unit, output_unit)
        record["canonical_stats"] = _stats([convert(value) for value in values])
    return record


def build(source: Path, field_manifest: Path, output: Path, prefix: str) -> dict[str, Any]:
    manifest = json.loads(field_manifest.read_text(encoding="utf-8"))
    fields_meta = dict(manifest.get("fields") or {})
    fields: dict[str, Any] = {}
    for slug in DIRECT_FIELDS:
        fields[slug] = _field_record(source, prefix, slug, fields_meta[slug], True)
    for slug in COMPARISON_ONLY_FIELDS:
        fields[slug] = _field_record(source, prefix, slug, fields_meta[slug], False)

    eject = fields["time_to_reach_ejection_temperature_part"]["canonical_stats"]
    eject_alt = fields["time_to_ejection_temp"]["canonical_stats"]
    nodal_t = fields["temperature_nodal"]["canonical_stats"]
    part_t = fields["temperature_part"]["canonical_stats"]
    frozen_last = fields["frozen_layer_fraction_last"]
    coolant = fields["circuit_coolant_temperature"]["canonical_stats"]
    metal = fields["circuit_metal_temperature"]["canonical_stats"]
    final_times = frozen_last["independent_values"]
    result = {
        "schema": "clawstack.mf_cooling_reference.v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "study": manifest.get("study"),
        "accuracy_label": "PROXY_GAP",
        "never_claim": "MOLDFLOW_EQUIVALENT",
        "fields": fields,
        "excluded_fields": {
            slug: {"reason": reason, "solver_role": "EXCLUDED_FROM_CALIBRATION"}
            for slug, reason in EXCLUDED_FIELDS.items()
        },
        "openfoam_targets": {
            "ejection_time_mean_s": eject["mean"],
            "ejection_time_p95_s": eject["p95"],
            "ejection_time_max_alt_s": eject_alt["max"],
            "cooling_horizon_s": max(final_times) if final_times else None,
            "part_temperature_mean_at_result_K": nodal_t["mean"],
            "part_temperature_p95_at_result_K": part_t["p95"],
            "part_temperature_max_at_result_K": part_t["max"],
            "coolant_temperature_mean_K": coolant["mean"],
            "circuit_metal_temperature_mean_K": metal["mean"],
        },
        "promotion_gates": {
            "ejection_time_relative_error_max": 0.10,
            "part_temperature_mae_K_max": 5.0,
            "frozen_fraction_mae_max": 0.05,
            "independent_repeat_runs_min": 2,
        },
        "scope_limits": [
            "Shrinkage, sink index, and circuit flow remain source-raw because units are unverified.",
            "The excluded temperature-difference field must be re-exported with delta-temperature semantics.",
            "This reference does not validate the current OpenFOAM thermal model.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--field-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prefix", default="mf_strip_cool_v12_20260720_1")
    args = parser.parse_args()
    result = build(args.source.resolve(), args.field_manifest.resolve(), args.output.resolve(), args.prefix)
    print(json.dumps({"output": str(args.output), "targets": result["openfoam_targets"], "accuracy_label": result["accuracy_label"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
