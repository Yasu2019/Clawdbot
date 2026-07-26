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
    parser.add_argument("--fbx", nargs="+", required=True)
    parser.add_argument("--report", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def inspect_fbx(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    rigs = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    actions = list(bpy.data.actions)
    result = {
        "file": str(path),
        "armatures": len(rigs),
        "actions": len(actions),
        "bones": [],
        "action_details": [],
    }
    if rigs:
        result["bones"] = [bone.name for bone in rigs[0].data.bones]
    for action in actions:
        slots = getattr(action, "slots", [])
        result["action_details"].append({
            "name": action.name,
            "frame_range": [float(v) for v in action.frame_range],
            "slots": len(slots),
        })
    result["pass"] = (
        len(rigs) == 1
        and len(result["bones"]) >= 15
        and len(actions) >= 1
        and any(item["frame_range"][1] > item["frame_range"][0] for item in result["action_details"])
    )
    return result


def main():
    args = parse_args()
    results = [inspect_fbx(Path(value).resolve()) for value in args.fbx]
    report = {
        "animations": results,
        "quality_gate": "PASS" if all(item["pass"] for item in results) else "FAIL",
    }
    Path(args.report).resolve().write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if report["quality_gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
