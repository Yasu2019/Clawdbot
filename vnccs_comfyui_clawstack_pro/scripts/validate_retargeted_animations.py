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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True)
    parser.add_argument("--fbx", required=True)
    parser.add_argument("--report", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def inspect(label, path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if label == "GLB":
        bpy.ops.import_scene.gltf(filepath=str(path))
    else:
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    materials = {
        material.name
        for obj in meshes
        for material in obj.data.materials
        if material is not None
    }
    actions = []
    for action in bpy.data.actions:
        start, end = [float(value) for value in action.frame_range]
        if end > start:
            actions.append({
                "name": action.name,
                "frame_range": [start, end],
                "duration": end - start,
            })
    bones = set()
    for rig in rigs:
        bones.update(bone.name for bone in rig.data.bones)
    expected_tokens = {"idle", "walking", "talking"}
    found_tokens = {
        token
        for token in expected_tokens
        if any(token in item["name"].lower() for item in actions)
    }
    result = {
        "format": label,
        "armatures": len(rigs),
        "mesh_objects": len(meshes),
        "materials": len(materials),
        "bones": len(bones),
        "actions": actions,
        "expected_actions_found": sorted(found_tokens),
    }
    result["pass"] = (
        len(rigs) == 1
        and len(meshes) >= 1
        and len(materials) >= 8
        and len(bones) == 19
        and found_tokens == expected_tokens
        and len(actions) >= 3
    )
    return result


def main():
    args = parse_args()
    glb_path = Path(args.glb).resolve()
    fbx_path = Path(args.fbx).resolve()
    report = {
        "glb": inspect("GLB", glb_path),
        "fbx": inspect("FBX", fbx_path),
    }
    report["quality_gate"] = (
        "PASS_MIXAMO3_RETARGET"
        if report["glb"]["pass"] and report["fbx"]["pass"]
        else "FAIL"
    )
    Path(args.report).resolve().write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["quality_gate"] == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
