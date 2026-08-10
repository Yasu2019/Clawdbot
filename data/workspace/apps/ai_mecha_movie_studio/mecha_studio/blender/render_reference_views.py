# -*- coding: utf-8 -*-
"""Blender headless script: FBX/GLB/OBJを読み込み、正面/背面/左右/斜めの参照PNGを自動生成。"""
import bpy
import sys
import math
from pathlib import Path
from mathutils import Vector


def args_after_double_dash():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


def import_model(path: Path):
    ext = path.suffix.lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".obj":
        try:
            bpy.ops.wm.obj_import(filepath=str(path))
        except Exception:
            bpy.ops.import_scene.obj(filepath=str(path))
    else:
        raise RuntimeError(f"未対応形式: {ext}")


def mesh_bounds():
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not objs:
        raise RuntimeError("メッシュがありません")
    points = []
    for o in objs:
        points.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
    mins = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maxs = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return (mins + maxs) / 2, (maxs - mins).length


def look_at(cam, target):
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def main():
    argv = args_after_double_dash()
    if len(argv) < 2:
        raise SystemExit("usage: model_path output_dir")
    model_path, out_dir = Path(argv[0]), Path(argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_model(model_path)
    center, size = mesh_bounds()

    bpy.ops.object.camera_add(location=(0, -size * 1.8, center.z))
    cam = bpy.context.object
    bpy.context.scene.camera = cam

    bpy.ops.object.light_add(type="AREA", location=(size, -size, center.z + size))
    key = bpy.context.object
    key.data.energy = 1500
    key.data.shape = "DISK"
    key.data.size = size

    bpy.ops.object.light_add(type="AREA", location=(-size, -size, center.z + size * 0.5))
    fill = bpy.context.object
    fill.data.energy = 900
    fill.data.size = size

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.context.scene, "eevee") else scene.render.engine
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True

    views = {
        "front": (0, -size * 1.8, center.z),
        "back": (0, size * 1.8, center.z),
        "left": (-size * 1.8, 0, center.z),
        "right": (size * 1.8, 0, center.z),
        "front_left": (-size * 1.3, -size * 1.3, center.z + size * 0.15),
        "front_right": (size * 1.3, -size * 1.3, center.z + size * 0.15),
    }
    for name, loc in views.items():
        cam.location = loc
        look_at(cam, center)
        scene.render.filepath = str(out_dir / f"{name}.png")
        bpy.ops.render.render(write_still=True)

if __name__ == "__main__":
    main()
