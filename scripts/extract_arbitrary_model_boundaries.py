"""Extract reusable gate/vent/wall/hole/inner/outer boundary groups from a surface model.

The extractor is intentionally sidecar-driven: a geometry file supplies the
triangulated surface and a JSON spec supplies physical gate/vent/hole
definitions.  This avoids hard-coded box coordinates and makes the same
classification path reusable for future STL/STEP-derived meshes once a STEP
triangulator has produced the surface.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import meshio
import numpy as np


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise ValueError("zero-length vector")
    return vector / norm


def load_tri_surface(path: Path) -> tuple[np.ndarray, np.ndarray]:
    suffix = path.suffix.lower()
    if suffix in {".step", ".stp"}:
        raise ValueError("STEP input requires prior triangulation to STL/VTU/PLY or an OCC triangulation plugin")
    mesh = meshio.read(path)
    triangles = []
    for block in mesh.cells:
        if block.type == "triangle":
            triangles.append(np.asarray(block.data, dtype=int))
        elif block.type == "quad":
            quads = np.asarray(block.data, dtype=int)
            triangles.append(np.column_stack([quads[:, 0], quads[:, 1], quads[:, 2]]))
            triangles.append(np.column_stack([quads[:, 0], quads[:, 2], quads[:, 3]]))
    if not triangles:
        raise ValueError(f"no triangle/quad surface cells in {path}")
    tri = np.vstack(triangles)
    pts = np.asarray(mesh.points[:, :3], dtype=float)
    if not np.isfinite(pts).all():
        raise ValueError("surface contains non-finite points")
    return pts, tri


def face_geometry(points: np.ndarray, triangles: np.ndarray) -> dict:
    a = points[triangles[:, 0]]
    b = points[triangles[:, 1]]
    c = points[triangles[:, 2]]
    cross = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(cross, axis=1)
    if np.any(area <= 0):
        raise ValueError("degenerate surface triangles are not accepted")
    normals = cross / (2.0 * area)[:, None]
    centroids = (a + b + c) / 3.0
    return {"centroids": centroids, "normals": normals, "areas": area}


def _circle_mask(centroids: np.ndarray, normals: np.ndarray, item: dict, *, default_tol: float) -> np.ndarray:
    center = np.asarray(item["center"], dtype=float)
    normal = _unit(np.asarray(item["normal"], dtype=float))
    radius = 0.5 * float(item["diameter"])
    plane_tol = float(item.get("plane_tolerance", default_tol))
    radius_tol = float(item.get("radius_tolerance", default_tol))
    rel = centroids - center
    plane_distance = np.abs(rel @ normal)
    radial = np.linalg.norm(rel - np.outer(rel @ normal, normal), axis=1)
    orientation = np.abs(normals @ normal)
    return (plane_distance <= plane_tol) & (radial <= radius + radius_tol) & (orientation >= float(item.get("min_normal_alignment", 0.45)))


def _cylinder_mask(centroids: np.ndarray, normals: np.ndarray, item: dict, *, default_tol: float) -> np.ndarray:
    center = np.asarray(item["center"], dtype=float)
    axis = _unit(np.asarray(item["axis"], dtype=float))
    radius = float(item["radius"])
    half_length = 0.5 * float(item.get("length", 1e30))
    tol = float(item.get("radius_tolerance", default_tol))
    rel = centroids - center
    axial = rel @ axis
    radial_vec = rel - np.outer(axial, axis)
    radial = np.linalg.norm(radial_vec, axis=1)
    tangent_normal = np.abs(normals @ axis) <= float(item.get("max_axis_alignment", 0.65))
    return (np.abs(axial) <= half_length + tol) & (np.abs(radial - radius) <= tol) & tangent_normal


def classify(points: np.ndarray, triangles: np.ndarray, spec: dict) -> dict:
    geom = face_geometry(points, triangles)
    centroids = geom["centroids"]
    normals = geom["normals"]
    areas = geom["areas"]
    centre = points.mean(axis=0)
    bbox_diag = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    default_tol = float(spec.get("tolerance", max(bbox_diag * 1e-3, 1e-9)))

    assigned = np.full(len(triangles), "", dtype=object)
    groups: dict[str, list[int]] = {}

    def put(name: str, mask: np.ndarray) -> None:
        free = mask & (assigned == "")
        ids = np.flatnonzero(free).astype(int)
        groups[name] = ids.tolist()
        assigned[ids] = name

    for prefix, items in (("gate", spec.get("gates", [])), ("vent", spec.get("vents", []))):
        for i, item in enumerate(items, start=1):
            put(str(item.get("name", f"{prefix}_{i}")), _circle_mask(centroids, normals, item, default_tol=default_tol))
    for i, item in enumerate(spec.get("holes", []), start=1):
        put(str(item.get("name", f"hole_{i}")), _cylinder_mask(centroids, normals, item, default_tol=default_tol))

    remaining = assigned == ""
    outward = np.einsum("ij,ij->i", normals, centroids - centre) >= 0
    put("outer_wall", remaining & outward)
    put("inner_wall", remaining & ~outward)

    area_by_group = {name: float(areas[ids].sum()) for name, ids in groups.items()}
    all_count = sum(len(ids) for ids in groups.values())
    checks = {
        "all_faces_classified_once": all_count == len(triangles),
        "gate_count": len(spec.get("gates", [])),
        "vent_count": len(spec.get("vents", [])),
        "hole_count": len(spec.get("holes", [])),
        "empty_required_groups": [name for name, ids in groups.items() if not ids and (name.startswith(("gate", "vent")))],
    }
    return {
        "schema": "clawstack.arbitrary.boundary.groups.v1",
        "status": "PASS" if checks["all_faces_classified_once"] and not checks["empty_required_groups"] else "HOLD",
        "units": spec.get("units", "model_units"),
        "face_count": int(len(triangles)),
        "node_count": int(len(points)),
        "groups": groups,
        "area_by_group": area_by_group,
        "checks": checks,
        "limitations": [
            "STL/mesh surface classification uses sidecar physical features; raw STEP must be triangulated first",
            "inner/outer wall split is normal/centroid based and should be audited for multi-cavity or non-manifold models",
        ],
    }


def run(model: Path, spec_path: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    points, triangles = load_tri_surface(model)
    result = classify(points, triangles, spec)
    output_dir.mkdir(parents=True)
    (output_dir / "boundary_groups_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(run(**vars(parser.parse_args())), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
