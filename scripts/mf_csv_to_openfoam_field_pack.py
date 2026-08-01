# -*- coding: utf-8 -*-
"""Build a traceable spatial-field pack from Moldflow nodal CSV exports.

The pack is an intermediate OpenFOAM input artifact. It preserves Moldflow
node IDs, attaches undeformed XYZ coordinates, converts only verified units,
and writes OpenFOAM ASCII point/scalar/vector lists. A solver case must still
map these volume points to its own cell centres before using them as fields.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/workspace/moldflow_bridge/mf_minusx_copy_results_20260801"
DEFAULT_XYZ = (
    ROOT
    / "data/workspace/moldflow_bridge/mf_all_results_20260730"
    / "mf_fc_warp_v2_20260720_warp_all_nodes.csv"
)
DEFAULT_OUTPUT = DEFAULT_SOURCE / "openfoam_field_pack_v1"
SENTINEL_ABS = 1.0e30


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def as_float(value: str | None) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except ValueError:
        return None
    if number is None or not math.isfinite(number) or abs(number) >= SENTINEL_ABS:
        return None
    return number


def load_xyz(path: Path) -> dict[int, tuple[float, float, float]]:
    points: dict[int, tuple[float, float, float]] = {}
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = set(reader.fieldnames or [])
        if {"NodeID", "X_before", "Y_before", "Z_before"} <= columns:
            id_col, xyz_cols = "NodeID", ("X_before", "Y_before", "Z_before")
        elif {"node_id", "x", "y", "z"} <= columns:
            id_col, xyz_cols = "node_id", ("x", "y", "z")
        else:
            raise ValueError(f"unsupported XYZ columns: {sorted(columns)}")
        for row in reader:
            node_id = int(row[id_col])
            points[node_id] = tuple(float(row[c]) for c in xyz_cols)  # type: ignore[assignment]
    if not points:
        raise ValueError("XYZ source contains no points")
    return points


ScalarConvert = Callable[[float], float]
FIELD_RULES: dict[str, dict[str, Any]] = {
    "fill_time": {"kind": "scalar", "source_unit": "s", "of_unit": "s", "convert": float},
    "freeze_time": {"kind": "scalar", "source_unit": "s", "of_unit": "s", "convert": float},
    "pressure": {"kind": "scalar", "source_unit": "MPa", "of_unit": "Pa", "convert": lambda v: v * 1.0e6},
    "pressure_vp_switchover": {"kind": "scalar", "source_unit": "MPa", "of_unit": "Pa", "convert": lambda v: v * 1.0e6},
    "temperature": {"kind": "scalar", "source_unit": "degC", "of_unit": "K", "convert": lambda v: v + 273.15},
    "temperature_at_flow_front": {"kind": "scalar", "source_unit": "degC", "of_unit": "K", "convert": lambda v: v + 273.15},
    "temperature_for_warp": {"kind": "scalar", "source_unit": "degC", "of_unit": "K", "convert": lambda v: v + 273.15},
    "viscosity": {"kind": "scalar", "source_unit": "Pa.s", "of_unit": "Pa.s", "convert": float},
    "density_fill": {"kind": "scalar", "source_unit": "g/cm3", "of_unit": "kg/m3", "convert": lambda v: v * 1000.0},
    "density_last": {"kind": "scalar", "source_unit": "g/cm3", "of_unit": "kg/m3", "convert": lambda v: v * 1000.0},
    "polymer_fill_region": {"kind": "scalar", "source_unit": "1", "of_unit": "1", "convert": float},
    "air_traps": {"kind": "scalar", "source_unit": "1", "of_unit": "1", "convert": float},
    "volumetric_shrinkage": {"kind": "scalar", "source_unit": "%", "of_unit": "%", "convert": float},
    "volumetric_shrinkage_warp": {"kind": "scalar", "source_unit": "%", "of_unit": "%", "convert": float},
    "shear_rate": {"kind": "scalar", "source_unit": "1/s", "of_unit": "1/s", "convert": float},
    "shear_rate_maximum": {"kind": "scalar", "source_unit": "1/s", "of_unit": "1/s", "convert": float},
    "velocity": {"kind": "vector", "source_unit": "UNVERIFIED", "of_unit": "UNVERIFIED", "convert": float},
    "melt_flow_direction_warp": {"kind": "vector", "source_unit": "1", "of_unit": "1", "convert": float},
}


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


def build(source: Path, xyz_path: Path, output: Path) -> dict[str, Any]:
    xyz_mm = load_xyz(xyz_path)
    output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "clawstack.mf_openfoam_spatial_field_pack.v1",
        "built_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "accuracy_band": "PROXY_GAP",
        "never_claim": "MOLDFLOW_EQUIVALENT",
        "coordinate_source": {"path": str(xyz_path), "sha256": sha256(xyz_path), "unit": "mm"},
        "coordinate_output_unit": "m",
        "fields": {},
        "limitations": [
            "This is a spatial point pack, not a solved OpenFOAM field.",
            "Map to the exact target case cell centres and enforce distance/extrapolation gates before solver use.",
            "Velocity source unit is unverified and is not safe for direct solver injection.",
        ],
    }
    csv_paths = sorted(list((source / "eval").glob("*.csv")) + list((source / "all_results").glob("*.csv")))
    for path in csv_paths:
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        if not rows:
            continue
        field = str(rows[0].get("field") or "").strip()
        rule = FIELD_RULES.get(field)
        if not rule:
            continue
        vector = rule["kind"] == "vector"
        joined: list[tuple[int, tuple[float, float, float], Any]] = []
        invalid = 0
        source_node_ids: set[int] = set()
        coordinate_missing = 0
        for row in rows:
            try:
                node_id = int(row["NodeID"])
            except (KeyError, TypeError, ValueError):
                invalid += 1
                continue
            source_node_ids.add(node_id)
            point_mm = xyz_mm.get(node_id)
            if point_mm is None:
                coordinate_missing += 1
                continue
            if vector:
                raw = tuple(as_float(row.get(k)) for k in ("vx", "vy", "vz"))
                if any(v is None for v in raw):
                    invalid += 1
                    continue
                value = tuple(rule["convert"](v) for v in raw)  # type: ignore[arg-type]
            else:
                raw_value = as_float(row.get("value"))
                if raw_value is None:
                    invalid += 1
                    continue
                value = rule["convert"](raw_value)
            point_m = tuple(v * 0.001 for v in point_mm)
            joined.append((node_id, point_m, value))
        if not joined:
            continue
        field_dir = output / field
        field_dir.mkdir(parents=True, exist_ok=True)
        points = [entry[1] for entry in joined]
        values = [entry[2] for entry in joined]
        write_foam_list(field_dir / "points", "vectorField", "points", points)
        write_foam_list(field_dir / "values", "vectorField" if vector else "scalarField", field, values)
        with (field_dir / "joined.csv").open("w", encoding="utf-8", newline="") as fh:
            columns = ["NodeID", "x_m", "y_m", "z_m"] + (["vx", "vy", "vz"] if vector else ["value"])
            writer = csv.writer(fh)
            writer.writerow(columns)
            for node_id, point, value in joined:
                writer.writerow([node_id, *point, *(value if vector else (value,))])
        manifest["fields"][field] = {
            "kind": rule["kind"],
            "source": str(path),
            "source_sha256": sha256(path),
            "source_unit": rule["source_unit"],
            "output_unit": rule["of_unit"],
            "rows": len(rows),
            "joined": len(joined),
            "coordinate_missing": coordinate_missing,
            "invalid_or_sentinel_values": invalid,
            "coordinate_join_fraction": round(
                (len(source_node_ids) - coordinate_missing) / len(source_node_ids), 8
            ),
            "valid_value_fraction": round(len(joined) / len(rows), 8),
            "safe_for_direct_mapping": rule["of_unit"] != "UNVERIFIED",
        }
    manifest["field_count"] = len(manifest["fields"])
    manifest["all_coordinates_joined"] = bool(manifest["fields"]) and all(
        f["coordinate_join_fraction"] == 1.0 for f in manifest["fields"].values()
    )
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--xyz", type=Path, default=DEFAULT_XYZ)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.source.resolve(), args.xyz.resolve(), args.output.resolve())
    print(json.dumps({"output": str(args.output), "field_count": manifest["field_count"], "all_coordinates_joined": manifest["all_coordinates_joined"]}, ensure_ascii=False))
    return 0 if manifest["field_count"] and manifest["all_coordinates_joined"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
