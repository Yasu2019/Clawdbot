"""Build a fail-closed BoundaryContract from an arbitrary surface model.

The extractor is intentionally sidecar-driven: a geometry file supplies the
triangulated surface and a JSON spec supplies physical gate/vent/hole
definitions.  STEP is tessellated with Open CASCADE when available.  The
output includes one STL per non-empty patch plus a machine-readable contract
that an OpenFOAM case builder can consume; a HOLD result exits non-zero.
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
import json
import math
import re
import tempfile
from pathlib import Path

import meshio
import numpy as np


def _unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise ValueError("zero-length vector")
    return vector / norm


def _triangulate_step_to_stl(step_path: Path, stl_path: Path, *, linear_deflection: float = 0.15) -> None:
    try:
        from OCP.BRepMesh import BRepMesh_IncrementalMesh
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPControl import STEPControl_Reader
        from OCP.StlAPI import StlAPI_Writer
    except ImportError as exc:
        raise RuntimeError(
            "STEP input needs the OCP package; install cadquery-ocp or provide a tessellated STL"
        ) from exc
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise ValueError(f"STEP read failed with status {status}: {step_path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError(f"STEP contains no transferable shape: {step_path}")
    BRepMesh_IncrementalMesh(shape, float(linear_deflection), True, 0.35, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(stl_path)):
        raise RuntimeError(f"STEP tessellation failed: {step_path}")


def load_tri_surface(path: Path, *, step_linear_deflection: float = 0.15) -> tuple[np.ndarray, np.ndarray]:
    suffix = path.suffix.lower()
    if suffix in {".step", ".stp"}:
        with tempfile.TemporaryDirectory(prefix="clawstack_step_") as temp_dir:
            stl_path = Path(temp_dir) / "surface.stl"
            _triangulate_step_to_stl(path, stl_path, linear_deflection=step_linear_deflection)
            mesh = meshio.read(stl_path)
    else:
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


def validate_surface(points: np.ndarray, triangles: np.ndarray) -> dict:
    """Validate topology without silently repairing or replacing geometry."""
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("triangles must have shape (n, 3)")
    if np.any(triangles < 0) or np.any(triangles >= len(points)):
        raise ValueError("triangle connectivity references an invalid point")
    edge_faces: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for face_id, tri in enumerate(triangles):
        for start, end in ((int(tri[0]), int(tri[1])), (int(tri[1]), int(tri[2])), (int(tri[2]), int(tri[0]))):
            key = (min(start, end), max(start, end))
            edge_faces.setdefault(key, []).append((face_id, 1 if start < end else -1))
    open_edges = [edge for edge, uses in edge_faces.items() if len(uses) == 1]
    nonmanifold_edges = [edge for edge, uses in edge_faces.items() if len(uses) > 2]
    orientation_conflicts = [
        edge for edge, uses in edge_faces.items()
        if len(uses) == 2 and uses[0][1] == uses[1][1]
    ]
    adjacency = [set() for _ in range(len(triangles))]
    for uses in edge_faces.values():
        ids = [face_id for face_id, _ in uses]
        for face_id in ids:
            adjacency[face_id].update(other for other in ids if other != face_id)
    unseen = set(range(len(triangles)))
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            current = stack.pop()
            neighbours = adjacency[current] & unseen
            unseen.difference_update(neighbours)
            stack.extend(neighbours)
    a = points[triangles[:, 0]]
    b = points[triangles[:, 1]]
    c = points[triangles[:, 2]]
    signed_volume = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    extent = np.ptp(points, axis=0)
    bbox_volume = float(np.prod(extent))
    volume_tolerance = float(max(bbox_volume * 1e-12, float(np.finfo(float).tiny)))
    checks = {
        "watertight": not open_edges and not nonmanifold_edges,
        "manifold": not nonmanifold_edges,
        "orientation_consistent": not orientation_conflicts,
        "nonzero_enclosed_volume": bool(abs(signed_volume) > volume_tolerance),
    }
    return {
        "checks": checks,
        "open_edge_count": len(open_edges),
        "nonmanifold_edge_count": len(nonmanifold_edges),
        "orientation_conflict_count": len(orientation_conflicts),
        "connected_component_count": components,
        "signed_volume_model_units3": signed_volume,
        "volume_tolerance_model_units3": volume_tolerance,
    }


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
    roles: dict[str, list[str]] = {"gate": [], "vent": [], "hole": [], "wall": []}

    def put(name: str, mask: np.ndarray, role: str) -> None:
        free = mask & (assigned == "")
        ids = np.flatnonzero(free).astype(int)
        groups[name] = ids.tolist()
        assigned[ids] = name
        roles[role].append(name)

    for prefix, items in (("gate", spec.get("gates", [])), ("vent", spec.get("vents", []))):
        for i, item in enumerate(items, start=1):
            put(str(item.get("name", f"{prefix}_{i}")), _circle_mask(centroids, normals, item, default_tol=default_tol), prefix)
    for i, item in enumerate(spec.get("holes", []), start=1):
        put(str(item.get("name", f"hole_{i}")), _cylinder_mask(centroids, normals, item, default_tol=default_tol), "hole")

    remaining = assigned == ""
    outward = np.einsum("ij,ij->i", normals, centroids - centre) >= 0
    put("outer_wall", remaining & outward, "wall")
    put("inner_wall", remaining & ~outward, "wall")

    area_by_group = {name: float(areas[ids].sum()) for name, ids in groups.items()}
    all_count = sum(len(ids) for ids in groups.values())
    required_groups = list(spec.get("required_groups", []))
    if not required_groups:
        required_groups = [
            str(item.get("name", f"{prefix}_{index}"))
            for prefix, items in (("gate", spec.get("gates", [])), ("vent", spec.get("vents", [])))
            for index, item in enumerate(items, start=1)
        ]
    empty_required = [name for name in required_groups if not groups.get(name)]
    checks = {
        "all_faces_classified_once": all_count == len(triangles),
        "gate_count": len(spec.get("gates", [])),
        "vent_count": len(spec.get("vents", [])),
        "hole_count": len(spec.get("holes", [])),
        "empty_required_groups": empty_required,
        "wall_face_count_positive": bool(groups.get("outer_wall") or groups.get("inner_wall")),
    }
    return {
        "schema": "clawstack.arbitrary.boundary.groups.v1",
        "status": "PASS" if checks["all_faces_classified_once"] and not checks["empty_required_groups"] and checks["wall_face_count_positive"] else "HOLD",
        "units": spec.get("units", "model_units"),
        "face_count": int(len(triangles)),
        "node_count": int(len(points)),
        "groups": groups,
        "roles": roles,
        "area_by_group": area_by_group,
        "checks": checks,
        "limitations": [
            "Gate, vent, and hole semantics come from explicit selectors; geometry alone cannot infer process intent",
            "inner/outer wall split is normal/centroid based and should be audited for multi-cavity or non-manifold models",
        ],
    }


def _safe_patch_name(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    if not safe or not re.match(r"[A-Za-z_]", safe):
        safe = "patch_" + safe
    return safe


def write_patch_artifacts(output_dir: Path, points: np.ndarray, triangles: np.ndarray, result: dict) -> dict:
    patch_dir = output_dir / "patch_surfaces"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patches = {}
    role_by_group = {
        group_name: role
        for role, group_names in result.get("roles", {}).items()
        for group_name in group_names
    }
    for group_name, face_ids in result["groups"].items():
        if not face_ids:
            continue
        patch_name = _safe_patch_name(group_name)
        path = patch_dir / f"{patch_name}.stl"
        subset = np.asarray(face_ids, dtype=int)
        meshio.write(path, meshio.Mesh(points=points, cells=[("triangle", triangles[subset])]), binary=False)
        patches[group_name] = {
            "patch_name": patch_name,
            "surface_file": str(path.relative_to(output_dir)).replace("\\", "/"),
            "face_count": len(face_ids),
            "area_model_units2": result["area_by_group"][group_name],
            "role": role_by_group.get(group_name, "wall"),
            "openfoam_patch_type": "patch" if role_by_group.get(group_name) in {"gate", "vent"} else "wall",
        }
    artifact = {
        "schema": "clawstack.openfoam.boundary.surface_artifacts.v1",
        "status": result["status"],
        "patches": patches,
        "consumer_contract": "Each surface_file is a separate snappyHexMesh geometry region; post-mesh face count and area must be reconciled before solve.",
    }
    (output_dir / "openfoam_patch_artifacts.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return artifact


def run(model: Path, spec_path: Path, output_dir: Path) -> dict:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    points, triangles = load_tri_surface(
        model,
        step_linear_deflection=float(spec.get("step_linear_deflection", 0.15)),
    )
    result = classify(points, triangles, spec)
    topology = validate_surface(points, triangles)
    result["surface_topology"] = topology
    result["model"] = {
        "path": str(model.resolve()),
        "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "suffix": model.suffix.lower(),
    }
    result["spec"] = {
        "path": str(spec_path.resolve()),
        "sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
    }
    topology_ok = all(topology["checks"].values())
    result["checks"]["surface_topology"] = topology_ok
    if not topology_ok:
        result["status"] = "HOLD"
    output_dir.mkdir(parents=True)
    result["openfoam_artifacts"] = write_patch_artifacts(output_dir, points, triangles, result)
    (output_dir / "boundary_groups_manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    report = run(**vars(parser.parse_args()))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
