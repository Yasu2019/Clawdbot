# -*- coding: utf-8 -*-
"""Blender headless: 部品を1つずつ強調表示してレンダし、部位を目視で同定できるようにする。

位置と寸法(bbox中心・幅)からの部位推定は、装甲板レベルになると外れる。
実例: part_8 を「腰+左右対称スカート」と推定してZ下側で切ったが、実際には
左右対称のスカート板にならず、細い左寄り部品が2つ出てきた。

そこで全体を灰色、対象部品だけを赤で塗ってレンダし、文脈込みで実体を確認する。

  blender --background --python render_part_atlas.py -- <fbx_or_blend> <out_dir> [views] [res]
      views: front,side,back,three_quarter のカンマ区切り（既定 front,side）
"""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

VIEW_DIRS = {
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "side": (-1.0, 0.0, 0.0),
    "three_quarter": (-0.75, -0.75, 0.15),
}


def argv_after():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def pick_engine(current):
    avail = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for n in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        if n in avail:
            return n
    return current


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return (mn + mx) / 2, (mx - mn)


def look_at(o, t):
    o.rotation_euler = (t - o.location).to_track_quat("-Z", "Y").to_euler()


def flat_material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = 0.7
    return m


def main():
    argv = argv_after()
    src, out_dir = Path(argv[0]), Path(argv[1])
    views = [v.strip() for v in (argv[2] if len(argv) > 2 else "front,side").split(",") if v.strip()]
    res = int(argv[3]) if len(argv) > 3 else 260
    out_dir.mkdir(parents=True, exist_ok=True)

    if src.suffix.lower() == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(src))
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(src))

    meshes = sorted([o for o in bpy.context.scene.objects if o.type == "MESH"], key=lambda m: m.name)
    center, span = bounds(meshes)
    size = span.length
    print(f"[atlas] parts={len(meshes)} views={views} res={res}")

    grey = flat_material("atlas_grey", (0.62, 0.63, 0.66))
    hot = flat_material("atlas_hot", (0.92, 0.13, 0.16))

    scene = bpy.context.scene
    scene.render.engine = pick_engine(scene.render.engine)
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False

    bpy.ops.object.light_add(type="SUN", location=(size, -size, center.z + size))
    k = bpy.context.object
    k.data.energy = 3.5
    look_at(k, center)
    bpy.ops.object.light_add(type="SUN", location=(-size, -size, center.z + size * 0.4))
    f = bpy.context.object
    f.data.energy = 1.6
    look_at(f, center)
    world = bpy.data.worlds.new("atlas")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.94, 0.96, 1.0)
    scene.world = world

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.clip_start = max(size * 0.001, 0.01)
    cam.data.clip_end = size * 10.0

    names = []
    for idx, target in enumerate(meshes):
        for o in meshes:
            o.data.materials.clear()
            o.data.materials.append(hot if o is target else grey)
        c, s = bounds([target])
        for view in views:
            dv = Vector(VIEW_DIRS.get(view, VIEW_DIRS["front"])).normalized()
            cam.location = center + dv * (size * 0.62)
            cam.location.z = center.z
            look_at(cam, center)
            path = out_dir / f"{idx:02d}_{view}_{target.name}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
        names.append(target.name)
        cen = ((c.x - (center.x - span.x / 2)) / span.x,
               (c.y - (center.y - span.y / 2)) / span.y,
               (c.z - (center.z - span.z / 2)) / span.z)
        print(f"[atlas] {idx:02d} {target.name:14} verts={len(target.data.vertices):6} "
              f"centroid=({cen[0]:.3f},{cen[1]:.3f},{cen[2]:.3f}) "
              f"size=({s.x/span.x:.3f},{s.y/span.y:.3f},{s.z/span.z:.3f})")

    (out_dir / "_order.txt").write_text("\n".join(f"{i:02d} {n}" for i, n in enumerate(names)),
                                        encoding="utf-8")
    print(f"[atlas] done -> {out_dir}")


if __name__ == "__main__":
    main()
