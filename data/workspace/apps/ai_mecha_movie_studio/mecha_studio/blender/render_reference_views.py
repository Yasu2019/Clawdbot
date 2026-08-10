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


def pick_engine(current):
    """実際に存在するレンダエンジン名を選ぶ。

    エンジンのenum名はBlenderの版で変わる（4.2系は BLENDER_EEVEE_NEXT、
    5.1では BLENDER_EEVEE に戻っている）。決め打ちすると
    TypeError: enum "..." not found で落ちるため、必ず実在候補から選ぶ。
    """
    available = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        if name in available:
            return name
    return current


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
    # クリップ面をモデル寸法に合わせる。FBXがcm単位だと18m級の機体で size≈1800 になり、
    # 既定の clip_end=100 では全部クリップされて真っ白（透過のみ）になる。
    cam.data.clip_start = max(size * 0.001, 0.01)
    cam.data.clip_end = size * 10.0

    # 照明は SUN + 環境光にする。点光源/エリアライトは照度が距離の二乗で変わるため、
    # モデルの単位系(m か cm か)で露出が破綻する。SUNは平行光なので距離に依存しない。
    bpy.ops.object.light_add(type="SUN", location=(size, -size, center.z + size))
    key = bpy.context.object
    key.data.energy = 4.0
    key.data.angle = math.radians(15)
    look_at(key, center)

    bpy.ops.object.light_add(type="SUN", location=(-size, -size, center.z + size * 0.5))
    fill = bpy.context.object
    fill.data.energy = 1.5
    fill.data.angle = math.radians(30)
    look_at(fill, center)

    world = bpy.data.worlds.new("ref_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.35, 0.37, 0.40, 1.0)
    bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world

    scene = bpy.context.scene
    scene.render.engine = pick_engine(scene.render.engine)
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
