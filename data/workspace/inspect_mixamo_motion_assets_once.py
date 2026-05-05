import json
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe")
MOTION_DIR = ROOT / "data/workspace/apps/motion_lab/assets/motions/raw/mixamo"
OUT_JSON = ROOT / "data/workspace/apps/motion_lab/04_motion_table/mixamo_motion_asset_inspection_20260503.json"


BLENDER_SCRIPT = r'''
import bpy
import json
from pathlib import Path

motion_paths = [Path(p) for p in __MOTION_PATHS__]
out_json = Path(r"__OUT_JSON__")


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for collection in (
        bpy.data.meshes,
        bpy.data.armatures,
        bpy.data.actions,
        bpy.data.objects,
    ):
        for item in list(collection):
            try:
                collection.remove(item)
            except Exception:
                pass


def inspect_file(path):
    clear_scene()
    result = {
        "name": path.name,
        "path": str(path),
        "ok": False,
        "armatures": [],
        "actions": [],
        "bone_samples": [],
        "frame_min": None,
        "frame_max": None,
        "error": None,
    }
    try:
        bpy.ops.import_scene.fbx(filepath=str(path))
        arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        result["armatures"] = [obj.name for obj in arms]
        bone_names = []
        for arm in arms:
            bone_names.extend([bone.name for bone in arm.data.bones])
        result["bone_samples"] = bone_names[:80]
        actions = []
        frame_min = None
        frame_max = None
        for action in bpy.data.actions:
            start, end = action.frame_range
            actions.append({"name": action.name, "frame_start": float(start), "frame_end": float(end)})
            frame_min = start if frame_min is None else min(frame_min, start)
            frame_max = end if frame_max is None else max(frame_max, end)
        result["actions"] = actions
        if frame_min is not None:
            result["frame_min"] = float(frame_min)
            result["frame_max"] = float(frame_max)
        result["ok"] = bool(arms and actions)
    except Exception as exc:
        result["error"] = str(exc)
    return result


results = [inspect_file(path) for path in motion_paths]
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def main() -> int:
    if not BLENDER.exists():
        raise FileNotFoundError(f"Blender not found: {BLENDER}")
    motion_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else MOTION_DIR
    out_json = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_JSON
    motions = sorted(motion_dir.glob("*.fbx"))
    if not motions:
        raise FileNotFoundError(f"No FBX files found in {motion_dir}")
    script = BLENDER_SCRIPT.replace(
        "__MOTION_PATHS__",
        json.dumps([str(path) for path in motions]),
    ).replace("__OUT_JSON__", str(out_json).replace("\\", "\\\\"))
    with tempfile.TemporaryDirectory(prefix="mixamo_inspect_") as temp_dir:
        script_path = Path(temp_dir) / "inspect_mixamo.py"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            [str(BLENDER), "--background", "--python", str(script_path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=900,
        )
    if result.returncode != 0:
        print(result.stdout[-4000:])
        print(result.stderr[-4000:])
        return result.returncode
    print(out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
