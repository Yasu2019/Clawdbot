# -*- coding: utf-8 -*-
"""Build a leakage-safe Moldflow structural benchmark for OF -> CalculiX.

Moldflow displacement, shrinkage, and temperature are reference-only.  They
are never emitted as CalculiX loads.  Predicted loads must come from an
independent OpenFOAM run so validation cannot silently soft-match the target.
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


FIELDS = {
    "warpage_reference": ("deflection_all_effects", "NODE"),
    "shrinkage_reference": ("volumetric_shrinkage_ejection", "TRI3"),
    "temperature_reference": ("temperature_nodal", "NODE"),
    "residual_stress_1_reference": ("in_cavity_residual_stress_in_first_principal_dir", "TRI3"),
    "residual_stress_2_reference": ("in_cavity_residual_stress_in_second_principal_di", "TRI3"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_nodes(path: Path) -> dict[int, tuple[float, float, float]]:
    nodes: dict[int, tuple[float, float, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            node = int(row["NodeID"])
            nodes[node] = (float(row["X_mm"]), float(row["Y_mm"]), float(row["Z_mm"]))
    if not nodes:
        raise ValueError("node coordinate export is empty")
    return nodes


def read_triangles(path: Path, nodes: dict[int, tuple[float, float, float]]) -> list[tuple[int, int, int, int]]:
    triangles: list[tuple[int, int, int, int]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["entity_type"].strip().upper() != "TRI3":
                continue
            conn = tuple(int(value) for value in row["node_connectivity"].split(";") if value)
            if len(conn) != 3:
                raise ValueError(f"bad TRI3 connectivity: {row}")
            missing = [node for node in conn if node not in nodes]
            if missing:
                raise ValueError(f"TRI3 {row['entity_id']} missing nodes {missing}")
            triangles.append((int(row["entity_id"]), conn[0], conn[1], conn[2]))
    if not triangles:
        raise ValueError("entity geometry contains no TRI3 elements")
    return triangles


def field_summary(path: Path, association: str, valid_ids: set[int]) -> dict[str, object]:
    values: list[float] = []
    ids: set[int] = set()
    columns: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        value_columns = [name for name in ("value", "vx", "vy", "vz", "mag") if name in columns]
        for row in reader:
            node = int(row["NodeID"])
            ids.add(node)
            for name in value_columns:
                value = float(row[name])
                if math.isfinite(value):
                    values.append(value)
    foreign = sorted(ids - valid_ids)
    if foreign:
        raise ValueError(f"{path.name} contains unknown {association} IDs: {foreign[:8]}")
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "columns": columns,
        "association": association,
        "entity_count": len(ids),
        "association_coverage": len(ids) / len(valid_ids),
        "numeric_min": min(values) if values else None,
        "numeric_max": max(values) if values else None,
        "role": "REFERENCE_ONLY_DO_NOT_USE_AS_SOLVER_LOAD",
    }


def choose_rigid_body_constraints(nodes: dict[int, tuple[float, float, float]]) -> tuple[int, int, int]:
    ordered = sorted(nodes)
    anchor = min(ordered, key=lambda node: sum(value * value for value in nodes[node]))
    second = max(ordered, key=lambda node: math.dist(nodes[node], nodes[anchor]))
    ax, ay, az = nodes[anchor]
    bx, by, bz = nodes[second]
    ab = (bx - ax, by - ay, bz - az)
    def area2(node: int) -> float:
        cx, cy, cz = nodes[node]
        ac = (cx - ax, cy - ay, cz - az)
        cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
        return sum(value * value for value in cross)
    third = max(ordered, key=area2)
    return anchor, second, third


def write_mesh_inp(path: Path, nodes: dict[int, tuple[float, float, float]], triangles: list[tuple[int, int, int, int]]) -> tuple[int, int, int]:
    anchor, second, third = choose_rigid_body_constraints(nodes)
    lines = [
        "** MF geometry only; reference fields are deliberately excluded",
        "** Units: mm, N, MPa. Material values are placeholders for parse/smoke tests.",
        "*NODE",
    ]
    lines.extend(f"{node},{xyz[0]:.12g},{xyz[1]:.12g},{xyz[2]:.12g}" for node, xyz in sorted(nodes.items()))
    lines.append("*ELEMENT,TYPE=S3,ELSET=CAVITY")
    lines.extend(f"{element},{n1},{n2},{n3}" for element, n1, n2, n3 in triangles)
    lines.extend([
        "*MATERIAL,NAME=PLACEHOLDER_PP",
        "*ELASTIC",
        "1400.,0.35",
        "*SHELL SECTION,ELSET=CAVITY,MATERIAL=PLACEHOLDER_PP",
        "2.0",
        "** Minimal rigid-body constraints only; replace material and add OF-derived loads",
        "*BOUNDARY",
        f"{anchor},1,3",
        f"{second},2,3",
        f"{third},3,3",
        "*STEP",
        "*STATIC",
        "*NODE FILE",
        "U",
        "*EL FILE",
        "S,E",
        "*END STEP",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return anchor, second, third


def locate_field(source: Path, prefix: str, slug: str) -> Path:
    candidate = source / f"{prefix}_{slug}.csv"
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--prefix", default="mf_strip_cool_v12_20260720_1")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    node_path = locate_field(source, args.prefix, "node_coordinates")
    geometry_path = locate_field(source, args.prefix, "entity_geometry")
    nodes = read_nodes(node_path)
    triangles = read_triangles(geometry_path, nodes)
    cavity_node_ids = {node for _, n1, n2, n3 in triangles for node in (n1, n2, n3)}
    cavity_nodes = {node: nodes[node] for node in cavity_node_ids}
    association_ids = {
        "NODE": cavity_node_ids,
        "TRI3": {element for element, _, _, _ in triangles},
    }
    inp = output / "mf_cavity_reference_mesh.inp"
    constraints = write_mesh_inp(inp, cavity_nodes, triangles)
    references = {}
    for name, (slug, association) in FIELDS.items():
        references[name] = field_summary(
            locate_field(source, args.prefix, slug),
            association,
            association_ids[association],
        )
    manifest = {
        "schema": "mf_structural_benchmark_pack_v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "accuracy_label": "PROXY_GAP",
        "validation_policy": {
            "moldflow_fields": "REFERENCE_ONLY_DO_NOT_USE_AS_SOLVER_LOAD",
            "solver_load_source": "INDEPENDENT_OPENFOAM_HISTORY_REQUIRED",
            "axis_soft_match": "FORBIDDEN",
            "global_scale_fit_on_validation_case": "FORBIDDEN",
        },
        "initial_promotion_gates": {
            "fill_time_relative_error_max": 0.05,
            "pressure_relative_error_max": 0.10,
            "temperature_mae_C_max": 5.0,
            "weldline_hausdorff_mm_max": 5.0,
            "sink_index_nrmse_max": 0.15,
            "warpage_vector_nrmse_max": 0.15,
            "warpage_peak_relative_error_max": 0.20,
            "independent_repeat_runs_min": 2,
        },
        "mesh": {
            "source_node_count": len(nodes),
            "cavity_node_count": len(cavity_nodes),
            "excluded_non_cavity_node_count": len(nodes) - len(cavity_nodes),
            "tri3_count": len(triangles),
            "node_source": str(node_path),
            "node_source_sha256": sha256(node_path),
            "geometry_source": str(geometry_path),
            "geometry_source_sha256": sha256(geometry_path),
            "calculix_mesh": str(inp),
            "calculix_mesh_sha256": sha256(inp),
            "rigid_body_constraint_nodes": constraints,
            "coordinate_unit": "mm",
        },
        "references": references,
        "scope_limits": [
            "Mesh deck contains placeholder elastic properties and no physical loads.",
            "This pack proves geometry/reference integrity, not solver accuracy.",
            "Promotion requires loads mapped from an independent OpenFOAM run.",
        ],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "cavity_nodes": len(cavity_nodes), "tri3": len(triangles), "references": len(references)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
