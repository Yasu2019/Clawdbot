# -*- coding: utf-8 -*-
"""Build the immutable V5 box-with-through-hole STEP and tetrahedral mesh."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import gmsh


AREA_REL_TOL = 5e-4


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(spec_path: Path, output_dir: Path, mesh_size_mm: float) -> dict:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    geometry = spec["geometry"]
    lx, ly, lz = map(float, geometry["outer_dimensions_mm"])
    diameter = float(geometry["hole_diameter_mm"])
    cx, cy = map(float, geometry["hole_center_mm"])
    process = spec["process"]
    gate_diameter = float(process["gate_diameter_mm"])
    gate_centers = [tuple(map(float, p)) for p in process["gate_coordinates_mm"]]
    vent_diameter = float(process["vent_diameter_mm"])
    vent_centers = [tuple(map(float, p)) for p in process["vent_coordinates_mm"]]
    output_dir.mkdir(parents=True, exist_ok=False)
    step_path = output_dir / "box_roundhole_v5.step"
    mesh_path = output_dir / "box_roundhole_v5.msh"

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.model.add("box_roundhole_v5")
        box = gmsh.model.occ.addBox(0.0, 0.0, 0.0, lx, ly, lz)
        # Canonical part is an open-top hollow container.  The inner box
        # reaches the top plane, leaving a 2 mm bottom and side walls.
        if geometry.get("open_top", False):
            ix, iy, iz = map(float, geometry["inner_dimensions_mm"])
            inner = gmsh.model.occ.addBox((lx-ix)/2.0, (ly-iy)/2.0, lz-iz, ix, iy, iz + 1e-6)
            shell, _ = gmsh.model.occ.cut([(3, box)], [(3, inner)], removeObject=True, removeTool=True)
            hole = gmsh.model.occ.addCylinder(cx, cy, -1.0, 0.0, 0.0, (lz-iz) + 2.0, diameter / 2.0)
            volumes, _ = gmsh.model.occ.cut(shell, [(3, hole)], removeObject=True, removeTool=True)
        else:
            hole = gmsh.model.occ.addCylinder(cx, cy, -1.0, 0.0, 0.0, lz + 2.0, diameter / 2.0)
            volumes, _ = gmsh.model.occ.cut([(3, box)], [(3, hole)], removeObject=True, removeTool=True)
        # Imprint exact circular inlet/outlet disks without partitioning the
        # volume.  A 2-D tool avoids internal volume interfaces and the
        # under-determined OpenFOAM cells those interfaces can create.
        imprint_tools = []
        for x, y, z, radius in [
            *[(x, y, z, gate_diameter / 2.0) for x, y, z in gate_centers],
            *[(x, y, z, vent_diameter / 2.0) for x, y, z in vent_centers],
        ]:
            disk = gmsh.model.occ.addDisk(x, y, z, radius, radius)
            gmsh.model.occ.rotate([(2, disk)], x, y, z, 0.0, 1.0, 0.0, 3.141592653589793 / 2.0)
            imprint_tools.append((2, disk))
        volumes, _ = gmsh.model.occ.fragment(volumes, imprint_tools, removeObject=True, removeTool=True)
        volumes = [(dim, tag) for dim, tag in volumes if dim == 3]
        gmsh.model.occ.synchronize()
        if not volumes:
            raise RuntimeError("volume fragmentation produced no volumes")
        volume_tags = [tag for _, tag in volumes]
        volume_group = gmsh.model.addPhysicalGroup(3, volume_tags)
        gmsh.model.setPhysicalName(3, volume_group, "polymer_cavity")
        surfaces = sorted({abs(tag) for dim, tag in gmsh.model.getBoundary(volumes, combined=True, oriented=True) if dim == 2})
        if geometry.get("open_top", False):
            gate_surfaces, vent_surfaces, wall_surfaces = [], [], []
            gate_area = 3.141592653589793 * (gate_diameter / 2.0) ** 2
            vent_area = 3.141592653589793 * (vent_diameter / 2.0) ** 2
            for tag in surfaces:
                xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.occ.getBoundingBox(2, tag)
                area = gmsh.model.occ.getMass(2, tag)
                if (abs(xmax - xmin) < 1e-6 and abs(xmin) < 1e-6
                        and abs(area - gate_area) / gate_area < AREA_REL_TOL):
                    gate_surfaces.append(tag)
                elif (abs(xmax - xmin) < 1e-6 and abs(xmin - lx) < 1e-6
                        and abs(area - vent_area) / vent_area < AREA_REL_TOL):
                    vent_surfaces.append(tag)
                else:
                    wall_surfaces.append(tag)
            if len(gate_surfaces) != len(gate_centers):
                end_face_areas = [
                    (tag, gmsh.model.occ.getMass(2, tag), gmsh.model.occ.getBoundingBox(2, tag))
                    for tag in surfaces
                    if abs(gmsh.model.occ.getBoundingBox(2, tag)[3]
                           - gmsh.model.occ.getBoundingBox(2, tag)[0]) < 1e-6
                ]
                raise RuntimeError(
                    f"expected {len(gate_centers)} circular gate surfaces, found {gate_surfaces}; "
                    f"planar end faces={end_face_areas}"
                )
            if len(vent_surfaces) != len(vent_centers):
                raise RuntimeError(f"expected {len(vent_centers)} circular vent surfaces, found {vent_surfaces}")
            for name, tags in (("gate", gate_surfaces), ("vent", vent_surfaces), ("cavity_wall", wall_surfaces)):
                if tags:
                    group = gmsh.model.addPhysicalGroup(2, tags)
                    gmsh.model.setPhysicalName(2, group, name)
        else:
            surface_group = gmsh.model.addPhysicalGroup(2, surfaces)
            gmsh.model.setPhysicalName(2, surface_group, "cavity_wall")
        gmsh.write(str(step_path))
        gmsh.option.setNumber("Mesh.MeshSizeMin", mesh_size_mm * 0.7)
        gmsh.option.setNumber("Mesh.MeshSizeMax", mesh_size_mm)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        # OpenFOAM gmshToFoam has the broadest interoperability with ASCII MSH 2.2.
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.option.setNumber("Mesh.Binary", 0)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(mesh_path))
        node_tags, _, _ = gmsh.model.mesh.getNodes()
        element_count = sum(len(tags) for tags in gmsh.model.mesh.getElements(3)[1])
        actual_volume = sum(gmsh.model.occ.getMass(3, tag) for tag in volume_tags)
    finally:
        gmsh.finalize()

    if geometry.get("open_top", False):
        ix, iy, iz = map(float, geometry["inner_dimensions_mm"])
        expected_volume = lx * ly * lz - ix * iy * iz - 3.141592653589793 * (diameter / 2.0) ** 2 * (lz - iz)
    else:
        expected_volume = lx * ly * lz - 3.141592653589793 * (diameter / 2.0) ** 2 * lz
    manifest = {
        "schema_version": "1.0",
        "model_id": spec["model_id"],
        "geometry_definition": geometry,
        "step_file": step_path.name,
        "step_sha256": sha256(step_path),
        "mesh_file": mesh_path.name,
        "mesh_sha256": sha256(mesh_path),
        "mesh_size_mm": mesh_size_mm,
        "nodes": len(node_tags),
        "volume_elements": element_count,
        "cad_volume_mm3": actual_volume,
        "analytic_volume_mm3": expected_volume,
        "volume_relative_error": abs(actual_volume - expected_volume) / expected_volume,
        "boundary_contract": {
            "gate_count": len(gate_centers),
            "gate_diameter_mm": gate_diameter,
            "gate_total_area_mm2": len(gate_centers) * 3.141592653589793 * (gate_diameter / 2.0) ** 2,
            "vent_count": len(vent_centers),
            "vent_diameter_mm": vent_diameter,
            "vent_total_area_mm2": len(vent_centers) * 3.141592653589793 * (vent_diameter / 2.0) ** 2,
        },
        "status": "GEOMETRY_ONLY_UNVALIDATED",
    }
    (output_dir / "geometry_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=Path("config/box_roundhole_v5_spec.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/box_roundhole_v5/geometry_l1"))
    parser.add_argument("--mesh-size-mm", type=float, default=2.0)
    args = parser.parse_args()
    if args.mesh_size_mm <= 0:
        parser.error("--mesh-size-mm must be positive")
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.output}")
    print(json.dumps(build(args.spec, args.output, args.mesh_size_mm), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
