# -*- coding: utf-8 -*-
"""Build an association-aware OpenFOAM reference pack from MF2010 CSVs.

The output contains point/value lists for comparison and later interpolation.
It never writes a solved OpenFOAM field and never claims Moldflow equivalence.
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
import itertools
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/workspace/moldflow_bridge/mf_coolflowwarp_all_results_20260802"
DEFAULT_GEOMETRY = DEFAULT_SOURCE / "mf_strip_cool_v12_20260720_1_entity_geometry.csv"
DEFAULT_COOLING_STL = Path(r"C:\Users\yasu\OneDrive\デスクトップ\Cooling_System_ASSY.stl")
DEFAULT_OUTPUT = DEFAULT_SOURCE / "openfoam_multiphysics_field_pack_v1"
STUDY_PREFIX = "mf_strip_cool_v12_20260720_1_"
SENTINEL_ABS = 1.0e30
ASSOCIATIONS = ("NODE", "TRI3", "1DET")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def finite(value: str | None) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    if number is None or not math.isfinite(number) or abs(number) >= SENTINEL_ABS:
        return None
    return number


def identity(value: float) -> float:
    return value


def mpa_to_pa(value: float) -> float:
    return value * 1.0e6


def degc_to_k(value: float) -> float:
    return value + 273.15


def mm_to_m(value: float) -> float:
    return value * 0.001


Rule = dict[str, Any]
RULES: dict[str, Rule] = {
    "pressure_end_of_fill": {"source_unit": "MPa", "output_unit": "Pa", "convert": mpa_to_pa},
    "hold_pressure": {"source_unit": "MPa", "output_unit": "Pa", "convert": mpa_to_pa},
    "frozen_pressure": {"source_unit": "MPa", "output_unit": "Pa", "convert": mpa_to_pa},
    "pressure_vp_switchover": {"source_unit": "MPa", "output_unit": "Pa", "convert": mpa_to_pa},
    "circuit_pressure": {"source_unit": "MPa", "output_unit": "Pa", "convert": mpa_to_pa},
    "bulk_temperature_eldt": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "bulk_temperature_eof": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "temperature_at_flow_front": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "temperature_nodal": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "temperature_mold": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "temperature_part": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "temperature_maximum_part": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "average_temperature_part": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "average_temperature_from_mold_walls": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "circuit_coolant_temperature": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "circuit_metal_temperature": {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k},
    "deflection_all_effects": {"source_unit": "mm", "output_unit": "m", "convert": mm_to_m},
    "time_to_ejection_temp": {"source_unit": "s", "output_unit": "s", "convert": identity},
    "time_to_reach_ejection_temperature_part": {"source_unit": "s", "output_unit": "s", "convert": identity},
    "shear_rate_bulk": {"source_unit": "1/s", "output_unit": "1/s", "convert": identity},
    "frozen_layer_fraction": {"source_unit": "1", "output_unit": "1", "convert": identity},
    "frozen_layer_eof": {"source_unit": "1", "output_unit": "1", "convert": identity},
    "orientation_at_core": {"source_unit": "1", "output_unit": "1", "convert": identity},
    "orientation_at_skin": {"source_unit": "1", "output_unit": "1", "convert": identity},
    "material_orientation": {"source_unit": "1", "output_unit": "1", "convert": identity},
}


def rule_for(field: str) -> Rule:
    rule = RULES.get(field)
    if rule:
        return {**rule, "unit_verified": True}
    if field.startswith("temperature_profile_part"):
        return {"source_unit": "degC", "output_unit": "K", "convert": degc_to_k, "unit_verified": True}
    return {
        "source_unit": "UNVERIFIED",
        "output_unit": "SOURCE_RAW",
        "convert": identity,
        "unit_verified": False,
    }


def load_geometry(path: Path) -> dict[str, dict[int, tuple[float, float, float]]]:
    geometry = {kind: {} for kind in ASSOCIATIONS}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            kind = row["entity_type"]
            if kind not in geometry:
                continue
            entity_id = int(row["entity_id"])
            if entity_id in geometry[kind]:
                raise ValueError(f"duplicate geometry key: {kind}:{entity_id}")
            geometry[kind][entity_id] = tuple(
                float(row[key]) * 0.001
                for key in ("centroid_x_mm", "centroid_y_mm", "centroid_z_mm")
            )
    if any(not geometry[kind] for kind in ASSOCIATIONS):
        raise ValueError("geometry must contain NODE, TRI3 and 1DET")
    return geometry


def choose_associations(ids: set[int], geometry: dict[str, dict[int, Any]]) -> tuple[str, ...]:
    if not ids:
        raise ValueError("field has no valid entity IDs")
    candidates: list[tuple[str, ...]] = []
    for size in range(1, len(ASSOCIATIONS) + 1):
        for combo in itertools.combinations(ASSOCIATIONS, size):
            covered = set().union(*(geometry[kind].keys() for kind in combo))
            if ids <= covered:
                candidates.append(combo)
        if candidates:
            break
    if not candidates:
        missing = sorted(ids - set().union(*(geometry[k].keys() for k in ASSOCIATIONS)))
        raise ValueError(f"unmapped entity IDs: {missing[:10]}")
    # Prefer the least surplus geometry when multiple one-type covers are possible.
    return min(candidates, key=lambda combo: sum(len(geometry[k]) for k in combo))


def foam_header(class_name: str, object_name: str) -> str:
    return (
        "FoamFile\n{\n    version 2.0;\n    format ascii;\n"
        f"    class {class_name};\n    object {object_name};\n}}\n"
    )


def write_foam_list(path: Path, class_name: str, object_name: str, values: list[Any]) -> None:
    lines = [foam_header(class_name, object_name), str(len(values)), "("]
    for value in values:
        if isinstance(value, tuple):
            lines.append(f"({value[0]:.12g} {value[1]:.12g} {value[2]:.12g})")
        else:
            lines.append(f"{value:.12g}")
    lines.extend((")", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def _result_files(source: Path) -> list[Path]:
    excluded = {"node_coordinates", "entity_geometry"}
    paths = []
    for path in sorted(source.glob(f"{STUDY_PREFIX}*.csv")):
        suffix = path.stem[len(STUDY_PREFIX):]
        if suffix not in excluded:
            paths.append(path)
    return paths


def build(source: Path, geometry_path: Path, output: Path, cooling_stl: Path | None = None) -> dict[str, Any]:
    geometry = load_geometry(geometry_path)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    manifest: dict[str, Any] = {
        "schema": "clawstack.mf_openfoam_multiphysics_field_pack.v1",
        "built_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "study": STUDY_PREFIX.rstrip("_"),
        "accuracy_band": "PROXY_GAP",
        "never_claim": "MOLDFLOW_EQUIVALENT",
        "geometry": {
            "path": str(geometry_path),
            "sha256": sha256(geometry_path),
            "coordinate_unit": "m",
            "counts": {kind: len(values) for kind, values in geometry.items()},
        },
        "cooling_stl": None,
        "fields": {},
        "limitations": [
            "Reference point/value lists only; not solved OpenFOAM volFields.",
            "Map/interpolate to the exact OpenFOAM mesh with distance and extrapolation gates.",
            "Fields with unit_verified=false remain source-raw and are comparison-only.",
            "Association geometry is NODE, TRI3 centroid, or 1DET centroid according to each dataset.",
        ],
    }
    if cooling_stl and cooling_stl.is_file():
        manifest["cooling_stl"] = {"path": str(cooling_stl), "sha256": sha256(cooling_stl), "unit": "mm_verified_by_bounds"}

    for path in _result_files(source):
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            continue
        field = str(rows[0].get("field") or path.stem[len(STUDY_PREFIX):]).strip()
        output_name = path.stem[len(STUDY_PREFIX):]
        vector = {"vx", "vy", "vz"} <= set(rows[0])
        valid_rows: list[tuple[int, Any]] = []
        invalid = 0
        for row in rows:
            try:
                entity_id = int(row["NodeID"])
            except (KeyError, TypeError, ValueError):
                invalid += 1
                continue
            if entity_id < 0:
                invalid += 1
                continue
            if vector:
                raw = tuple(finite(row.get(key)) for key in ("vx", "vy", "vz"))
                if any(value is None for value in raw):
                    invalid += 1
                    continue
                value = raw
            else:
                value = finite(row.get("value"))
                if value is None:
                    invalid += 1
                    continue
            valid_rows.append((entity_id, value))
        ids = {entity_id for entity_id, _ in valid_rows}
        associations = choose_associations(ids, geometry)
        rule = rule_for(field)
        convert: Callable[[float], float] = rule["convert"]
        joined: list[tuple[str, int, tuple[float, float, float], Any]] = []
        ambiguous = 0
        for entity_id, raw_value in valid_rows:
            matches = [kind for kind in associations if entity_id in geometry[kind]]
            if len(matches) != 1:
                ambiguous += 1
                continue
            kind = matches[0]
            value = tuple(convert(float(v)) for v in raw_value) if vector else convert(float(raw_value))
            joined.append((kind, entity_id, geometry[kind][entity_id], value))
        if ambiguous or len(joined) != len(valid_rows):
            raise ValueError(f"ambiguous/incomplete association for {output_name}: {ambiguous}")
        field_dir = output / output_name
        field_dir.mkdir()
        points = [row[2] for row in joined]
        values = [row[3] for row in joined]
        write_foam_list(field_dir / "points", "vectorField", f"{output_name}_points", points)
        write_foam_list(field_dir / "values", "vectorField" if vector else "scalarField", output_name, values)
        with (field_dir / "entity_ids.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(("entity_type", "entity_id"))
            writer.writerows((kind, entity_id) for kind, entity_id, _, _ in joined)
        manifest["fields"][output_name] = {
            "field": field,
            "kind": "vector" if vector else "scalar",
            "source": str(path),
            "source_sha256": sha256(path),
            "source_rows": len(rows),
            "valid_rows": len(valid_rows),
            "invalid_or_sentinel_rows": invalid,
            "joined_rows": len(joined),
            "join_fraction": 1.0,
            "associations": list(associations),
            "association_counts": {kind: sum(1 for row in joined if row[0] == kind) for kind in associations},
            "source_unit": rule["source_unit"],
            "output_unit": rule["output_unit"],
            "unit_verified": rule["unit_verified"],
            "safe_for_direct_solver_initialization": False,
            "comparison_ready": True,
        }
    manifest["field_count"] = len(manifest["fields"])
    manifest["all_fields_fully_joined"] = bool(manifest["fields"]) and all(
        field["join_fraction"] == 1.0 for field in manifest["fields"].values()
    )
    manifest["unit_verified_field_count"] = sum(
        bool(field["unit_verified"]) for field in manifest["fields"].values()
    )
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--geometry", type=Path, default=DEFAULT_GEOMETRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cooling-stl", type=Path, default=DEFAULT_COOLING_STL)
    args = parser.parse_args()
    manifest = build(args.source.resolve(), args.geometry.resolve(), args.output.resolve(), args.cooling_stl.resolve())
    summary = {
        "output": str(args.output),
        "field_count": manifest["field_count"],
        "all_fields_fully_joined": manifest["all_fields_fully_joined"],
        "unit_verified_field_count": manifest["unit_verified_field_count"],
        "accuracy_band": manifest["accuracy_band"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if manifest["field_count"] and manifest["all_fields_fully_joined"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

