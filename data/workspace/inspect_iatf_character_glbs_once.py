"""Inspect Bulma/Goku GLB files for Blender rig availability."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BLENDER = Path("C:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
OUT_DIR = ROOT / "data/workspace/iatf_bulma_goku_probe"
STATUS_PATH = ROOT / "data/workspace/iatf_bulma_goku_probe_status.json"
MODELS = {
    "bulma": ROOT / "data/workspace/iatf_remotion_studio/public/bulma_mc.glb",
    "goku": ROOT / "data/workspace/iatf_remotion_studio/public/goku.glb",
}


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def blender_script(out_dir: Path) -> str:
    models_json = json.dumps({k: str(v).replace("\\", "/") for k, v in MODELS.items()})
    out = str(out_dir).replace("\\", "/")
    return f'''
import bpy
import json
from pathlib import Path

OUT_DIR = Path(r"{out}")
MODELS = {models_json}
OUT_DIR.mkdir(parents=True, exist_ok=True)

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for collection in [bpy.data.meshes, bpy.data.armatures, bpy.data.materials, bpy.data.images]:
        for item in list(collection):
            collection.remove(item)

def inspect_model(name, path):
    clear_scene()
    result = {{
        "name": name,
        "path": path,
        "import_ok": False,
        "objects": [],
        "armatures": [],
        "meshes": [],
        "materials_count": 0,
        "sample_png": None,
        "error": None,
    }}
    try:
        bpy.ops.import_scene.gltf(filepath=path)
        result["import_ok"] = True
        result["materials_count"] = len(bpy.data.materials)
        for obj in bpy.context.scene.objects:
            result["objects"].append({{
                "name": obj.name,
                "type": obj.type,
                "parent": obj.parent.name if obj.parent else None,
            }})
            if obj.type == "ARMATURE":
                bones = []
                for bone in obj.data.bones:
                    bones.append({{
                        "name": bone.name,
                        "parent": bone.parent.name if bone.parent else None,
                    }})
                result["armatures"].append({{
                    "name": obj.name,
                    "bone_count": len(bones),
                    "bones_first_80": bones[:80],
                    "bone_names": [b["name"] for b in bones],
                }})
            elif obj.type == "MESH":
                result["meshes"].append({{
                    "name": obj.name,
                    "vertices": len(obj.data.vertices),
                    "polygons": len(obj.data.polygons),
                    "material_slots": len(obj.material_slots),
                }})

        bpy.ops.object.light_add(type="AREA", location=(0, -3, 4))
        light = bpy.context.object
        light.data.energy = 350
        light.data.size = 5
        bpy.ops.object.camera_add(location=(0, -5, 1.5))
        cam = bpy.context.object
        bpy.context.scene.camera = cam
        cam.rotation_euler = (1.35, 0, 0)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 3.0
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 16
        scene.render.resolution_x = 900
        scene.render.resolution_y = 900
        scene.view_settings.view_transform = "Standard"
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(OUT_DIR / f"{{name}}_preview.png")
        bpy.ops.render.render(write_still=True)
        result["sample_png"] = str(OUT_DIR / f"{{name}}_preview.png")
    except Exception as exc:
        result["error"] = str(exc)
    return result

results = [inspect_model(name, path) for name, path in MODELS.items()]
(OUT_DIR / "glb_inspection.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
'''


def main() -> int:
    if not BLENDER.exists():
        raise FileNotFoundError(f"Blender not found: {BLENDER}")
    missing = [str(path) for path in MODELS.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing models: " + ", ".join(missing))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_status("start", models={k: str(v) for k, v in MODELS.items()})
    with tempfile.TemporaryDirectory(prefix="iatf_glb_inspect_") as tmp:
        script_path = Path(tmp) / "inspect_glb.py"
        script_path.write_text(blender_script(OUT_DIR), encoding="utf-8")
        result = subprocess.run(
            [str(BLENDER), "--background", "--python", str(script_path)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        (OUT_DIR / "blender_stdout.log").write_text(result.stdout[-8000:], encoding="utf-8")
        (OUT_DIR / "blender_stderr.log").write_text(result.stderr[-8000:], encoding="utf-8")
        if result.returncode != 0:
            write_status("error", returncode=result.returncode, stderr=result.stderr[-1200:])
            return result.returncode
    data = json.loads((OUT_DIR / "glb_inspection.json").read_text(encoding="utf-8"))
    summary = {
        item["name"]: {
            "import_ok": item["import_ok"],
            "armatures": [(arm["name"], arm["bone_count"]) for arm in item["armatures"]],
            "mesh_count": len(item["meshes"]),
            "sample_png": item["sample_png"],
            "error": item["error"],
        }
        for item in data
    }
    write_status("done", ok=True, summary=summary, report=str(OUT_DIR / "glb_inspection.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
