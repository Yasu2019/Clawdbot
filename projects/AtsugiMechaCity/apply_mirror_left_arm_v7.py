# -*- coding: utf-8 -*-
"""
apply_mirror_left_arm_v7.py — enforce L/R arm pivot SYMMETRY. ① gives the left arm a
mis-placed shoulder pivot (z=14.9 vs right z=13.3), so the left arm contorts when
posed. Mirror the working RIGHT arm bone pivots to the LEFT (negate X), rebind, v7.

Run:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\apply_mirror_left_arm_v7.py -- ^
    --in D:\\Temp\\Zaku_AutoRig_v6.blend --out D:\\Temp\\Zaku_AutoRig_v7.blend
"""
import bpy
import sys
from pathlib import Path

_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag, default=None):
    if flag in _args:
        i = _args.index(flag)
        if i + 1 < len(_args):
            return _args[i + 1]
    return default


sys.path.insert(0, str(Path(__file__).resolve().parent))
import mecha_rig_builder as mrb  # noqa: E402

PAIRS = [("UpperArm_L", "UpperArm_R"), ("LowerArm_L", "LowerArm_R"), ("Hand_L", "Hand_R")]


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v6.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v7.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)

    bind, world, by_name = {}, {}, {}
    for o in scene.objects:
        if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
            bind[o.name] = o.parent_bone
            world[o.name] = o.matrix_world.copy()
            by_name[o.name] = o

    # unparent (keep world)
    bpy.ops.object.select_all(action="DESELECT")
    for n in bind:
        by_name[n].select_set(True)
    bpy.context.view_layer.objects.active = by_name[next(iter(bind))]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.context.view_layer.update()
    for n, m in world.items():
        by_name[n].matrix_world = m

    # mirror right arm bone pivots -> left (negate X of head & tail)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for lname, rname in PAIRS:
        lb, rb = eb.get(lname), eb.get(rname)
        if not lb or not rb:
            continue
        lb.head = (-rb.head.x, rb.head.y, rb.head.z)
        lb.tail = (-rb.tail.x, rb.tail.y, rb.tail.z)
        lb.roll = -rb.roll
        print(f"[V7] mirrored {rname} -> {lname}: head z {lb.head.z:.1f}")
    bpy.ops.object.mode_set(mode="OBJECT")

    # rebind
    for n, bone in bind.items():
        by_name[n].matrix_world = world[n]
        mrb.bind_segment(by_name[n], arm, bone)
    bpy.context.view_layer.update()

    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[V7] saved: {blend_out}")


if __name__ == "__main__":
    main()
