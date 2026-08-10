# -*- coding: utf-8 -*-
"""Blender headless: リグ付きメカFBXへ別FBXのモーションを移植し、連番PNGでレンダする。

同じ Mixamo 系リグ（ボーン名が `mixamorig:*`）どうしなら、アクションをそのまま
割り当てるだけでモーションが乗る。骨格名が違う場合はここでは扱わない
（別途リターゲットが必要）。

  blender --background --python render_walk_animation.py -- \
      <model_fbx> <motion_fbx> <out_dir> [views] [samples] [resolution]

  views      : front,side,back,three_quarter のカンマ区切り（既定 side）
  samples    : レンダするフレーム間引き。1=全フレーム（既定 1）
  resolution : 正方形1辺のピクセル数（既定 640）
"""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector


def args_after_double_dash():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1:]


def pick_engine(current):
    """実在するレンダエンジン名を選ぶ（版によって enum 名が変わるため決め打ち禁止）。"""
    available = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        if name in available:
            return name
    return current


def import_fbx(path: Path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(path))
    return [o for o in bpy.context.scene.objects if o not in before]


def find_armature(objs):
    for o in objs:
        if o.type == "ARMATURE":
            return o
    return None


def assign_action(target_arm, action):
    """アクションを対象アーマチュアへ割り当てる。

    Blender 4.4以降はスロット付きアクションになっており、action を代入するだけでは
    再生されない。slot も併せて割り当てる必要がある。
    """
    if target_arm.animation_data is None:
        target_arm.animation_data_create()
    target_arm.animation_data.action = action
    slots = getattr(action, "slots", None)
    if slots and hasattr(target_arm.animation_data, "action_slot"):
        for slot in slots:
            try:
                target_arm.animation_data.action_slot = slot
                break
            except Exception:
                continue


def mesh_bounds(objs):
    meshes = [o for o in objs if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("メッシュがありません")
    pts = []
    for o in meshes:
        pts.extend([o.matrix_world @ Vector(c) for c in o.bound_box])
    mins = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    maxs = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (mins + maxs) / 2, (maxs - mins).length


def look_at(obj, target):
    direction = target - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_lighting(center, size):
    """SUN + 環境光。点/エリア光は照度が距離二乗で変わり、FBXの単位系(m/cm)で露出が破綻する。"""
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

    world = bpy.data.worlds.new("walk_world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.32, 0.34, 0.38, 1.0)
    bg.inputs[1].default_value = 1.0
    bpy.context.scene.world = world


VIEW_DIRS = {
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "side": (-1.0, 0.0, 0.0),
    "three_quarter": (-0.75, -0.75, 0.12),
}


def main():
    argv = args_after_double_dash()
    if len(argv) < 3:
        raise SystemExit("usage: model_fbx motion_fbx out_dir [views] [samples] [resolution]")
    model_fbx = Path(argv[0])
    motion_fbx = Path(argv[1])
    out_root = Path(argv[2])
    views = [v.strip() for v in (argv[3] if len(argv) > 3 else "side").split(",") if v.strip()]
    step = int(argv[4]) if len(argv) > 4 else 1
    res = int(argv[5]) if len(argv) > 5 else 640

    bpy.ops.wm.read_factory_settings(use_empty=True)

    model_objs = import_fbx(model_fbx)
    target = find_armature(model_objs)
    if target is None:
        raise RuntimeError(f"アーマチュアが見つかりません: {model_fbx}")

    motion_objs = import_fbx(motion_fbx)
    source = find_armature(motion_objs)
    if source is None or source.animation_data is None or source.animation_data.action is None:
        raise RuntimeError(f"モーション側にアクションがありません: {motion_fbx}")
    action = source.animation_data.action

    target_bones = {b.name for b in target.data.bones}
    source_bones = {b.name for b in source.data.bones}
    shared = target_bones & source_bones
    print(f"[walk] target_bones={len(target_bones)} source_bones={len(source_bones)} shared={len(shared)}")
    if not shared:
        raise RuntimeError("ボーン名が一致しません。リターゲットが別途必要です")

    assign_action(target, action)

    # モーション供給元は描画しない（メッシュもアーマチュアも消す）
    bpy.ops.object.select_all(action="DESELECT")
    for o in motion_objs:
        o.select_set(True)
    bpy.ops.object.delete()

    start, end = (int(action.frame_range[0]), int(action.frame_range[1]))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = start, end
    scene.frame_set(start)

    center, size = mesh_bounds(model_objs)
    print(f"[walk] frames={start}..{end} step={step} size={size:.2f} center={tuple(round(v,2) for v in center)}")

    setup_lighting(center, size)

    # 接地感が無いと浮いて見えるので、足元に地面を敷く
    mins_z = min((o.matrix_world @ Vector(c)).z for o in model_objs if o.type == "MESH"
                 for c in o.bound_box)
    bpy.ops.mesh.primitive_plane_add(size=size * 8, location=(center.x, center.y, mins_z))
    ground = bpy.context.object
    mat = bpy.data.materials.new("ground")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.18, 0.19, 0.21, 1.0)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
    ground.data.materials.append(mat)

    bpy.ops.object.camera_add(location=(0, -size, center.z))
    cam = bpy.context.object
    scene.camera = cam
    # 既定 clip_end=100 では cm単位FBX(18m級=size~1800)が全クリップされ真っ白になる
    cam.data.clip_start = max(size * 0.001, 0.01)
    cam.data.clip_end = size * 10.0

    scene.render.engine = pick_engine(scene.render.engine)
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    written = 0
    for view in views:
        dir_vec = Vector(VIEW_DIRS.get(view, VIEW_DIRS["side"])).normalized()
        out_dir = out_root / view
        out_dir.mkdir(parents=True, exist_ok=True)
        for frame in range(start, end + 1, step):
            scene.frame_set(frame)
            # 歩行でルートが移動するので、フレームごとに構図を取り直す
            c, s = mesh_bounds(model_objs)
            cam.location = c + dir_vec * (s * 1.15)
            cam.location.z = c.z + s * 0.05
            look_at(cam, c)
            scene.render.filepath = str(out_dir / f"{view}_{frame:04d}.png")
            bpy.ops.render.render(write_still=True)
            written += 1
    print(f"[walk] rendered={written}")


if __name__ == "__main__":
    main()
