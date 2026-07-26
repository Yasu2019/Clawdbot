import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path

import bpy
import bmesh


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True)
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--report", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def inspect_scene(label):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    boundary = 0
    non_manifold = 0
    triangles = 0
    materials = set()
    vertex_groups = set()
    for obj in meshes:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        boundary += sum(1 for edge in bm.edges if edge.is_boundary)
        non_manifold += sum(1 for edge in bm.edges if not edge.is_manifold)
        bm.free()
        triangles += sum(max(1, len(poly.vertices) - 2) for poly in obj.data.polygons)
        materials.update(slot.name for slot in obj.data.materials if slot)
        vertex_groups.update(group.name for group in obj.vertex_groups)
    bones = set()
    for rig in rigs:
        bones.update(bone.name for bone in rig.data.bones)
    required = {
        "Hips", "Spine", "Chest", "Neck", "Head",
        "UpperArm.L", "LowerArm.L", "Hand.L",
        "UpperArm.R", "LowerArm.R", "Hand.R",
        "UpperLeg.L", "LowerLeg.L", "Foot.L",
        "UpperLeg.R", "LowerLeg.R", "Foot.R",
    }
    result = {
        "format": label,
        "mesh_objects": len(meshes),
        "armatures": len(rigs),
        "triangles": triangles,
        "materials": len(materials),
        "bones": len(bones),
        "required_bones_missing": sorted(required - bones),
        "vertex_groups": len(vertex_groups),
        "boundary_edges": boundary,
        "non_manifold_edges": non_manifold,
    }
    topology_pass = (
        True if label == "GLB"
        else boundary == 0 and non_manifold == 0
    )
    result["topology_rule"] = (
        "SOURCE_AND_FBX_AUTHORITATIVE_GLTF_SEAMS_MAY_SPLIT_VERTICES"
        if label == "GLB"
        else "REQUIRE_ZERO_BOUNDARY_AND_NON_MANIFOLD"
    )
    result["pass"] = (
        len(meshes) >= 1
        and len(rigs) == 1
        and len(materials) >= 8
        and not result["required_bones_missing"]
        and topology_pass
    )
    return result


def main():
    args = parse_args()
    results = {}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.glb).resolve()))
    results["glb"] = inspect_scene("GLB")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(Path(args.fbx).resolve()))
    results["fbx"] = inspect_scene("FBX")
    results["quality_gate"] = (
        "PASS_COMMERCIAL_STYLIZED"
        if results["glb"]["pass"] and results["fbx"]["pass"]
        else "FAIL"
    )
    report_path = Path(args.report).resolve()
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    if results["quality_gate"] == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
