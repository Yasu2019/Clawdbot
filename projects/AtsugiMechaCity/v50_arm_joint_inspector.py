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
from mathutils import Vector


GROUPS = {
    "TORSO": [
        "Torso_Core", "Pelvis_Center", "geometry_0", "geometry_0.001", "geometry_0.003",
        "geometry_0.004", "geometry_0.007", "geometry_0.010", "geometry_0.011", "geometry_0.015",
    ],
    "UPPER_ARM_L": ["geometry_0.012", "geometry_0.018", "geometry_0.020", "geometry_0.034"],
    "LOWER_ARM_L": ["geometry_0.005", "geometry_0.023", "geometry_0.032"],
    "HAND_L": [
        "V50_PROXY_Hand_L_Palm", "V50_PROXY_Hand_L_Palm_Core",
        "V50_PROXY_Hand_L_Finger_A", "V50_PROXY_Hand_L_Finger_B", "V50_PROXY_Hand_L_Finger_C",
    ],
    "UPPER_ARM_R": ["geometry_0.002", "geometry_0.019", "geometry_0.021", "geometry_0.022"],
    "LOWER_ARM_R": ["geometry_0.024", "geometry_0.033"],
    "HAND_R": ["geometry_0.006"],
}


MARKERS = {
    "shoulder_L": "V50_RIG_MARKER_shoulder_L",
    "elbow_L": "V50_RIG_MARKER_elbow_L",
    "wrist_L": "V50_RIG_MARKER_wrist_L",
    "shoulder_R": "V50_RIG_MARKER_shoulder_R",
    "elbow_R": "V50_RIG_MARKER_elbow_R",
    "wrist_R": "V50_RIG_MARKER_wrist_R",
}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def bounds_for(names):
    points = []
    missing = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            missing.append(name)
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        return {"missing": missing}
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    center = (lo + hi) * 0.5
    return {
        "lo": [round(float(lo[i]), 6) for i in range(3)],
        "hi": [round(float(hi[i]), 6) for i in range(3)],
        "center": [round(float(center[i]), 6) for i in range(3)],
        "missing": missing,
    }


def main():
    args = parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend)))
    bpy.context.scene.frame_set(int(bpy.context.scene.frame_start))
    bpy.context.view_layer.update()
    report = {
        "source_blend": str(Path(args.blend)),
        "groups": {name: bounds_for(names) for name, names in GROUPS.items()},
        "markers": {},
        "armatures": [],
    }
    for key, name in MARKERS.items():
        obj = bpy.data.objects.get(name)
        report["markers"][key] = ({
            "world": [round(float(obj.matrix_world.translation[i]), 6) for i in range(3)],
            "local": [round(float(obj.location[i]), 6) for i in range(3)],
            "parent": obj.parent.name if obj.parent else None,
            "type": obj.type,
        } if obj is not None else None)
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            report["armatures"].append({
                "name": obj.name,
                "bones": [bone.name for bone in obj.data.bones],
            })
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "armatures": len(report["armatures"])}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
