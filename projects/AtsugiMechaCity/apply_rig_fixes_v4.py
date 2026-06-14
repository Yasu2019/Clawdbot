# -*- coding: utf-8 -*-
"""
apply_rig_fixes_v4.py — apply roll-normalization + plate-armor follower reassignment
to v3 (which already has RULE① pivots) -> v4.

Fixes the two issues exposed when posing the arms down:
  - shoulder shield (plate on UpperArm) flings out  -> reassign plate armor to parent
  - inconsistent L/R bone rolls                      -> normalize_bone_rolls

Run:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\apply_rig_fixes_v4.py -- ^
    --in D:\\Temp\\Zaku_AutoRig_v3.blend --out D:\\Temp\\Zaku_AutoRig_v4.blend
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


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v3.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v4.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    if not arm:
        print("[V4] no armature"); return

    bind, world, by_name = {}, {}, {}
    for o in scene.objects:
        if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
            bind[o.name] = o.parent_bone
            world[o.name] = o.matrix_world.copy()
            by_name[o.name] = o
    print(f"[V4] captured {len(bind)} bound segments")

    # unparent (keep world)
    bpy.ops.object.select_all(action="DESELECT")
    for n in bind:
        by_name[n].select_set(True)
    bpy.context.view_layer.objects.active = by_name[next(iter(bind))]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.context.view_layer.update()
    for n, m in world.items():
        by_name[n].matrix_world = m

    # FIX A: plate-armor follower reassignment (mutates bind). ARMS ONLY — leg armor
    # (part_13_thigh_*) must swing WITH the leg, and the legs already pass the gate.
    moved = mrb.reassign_plate_armor_to_parent(
        arm, bind, by_name, limb_bones=("UpperArm_L", "UpperArm_R"))
    print(f"[V4] plate armor reassigned ({len(moved)}): {moved}")

    # FIX B (SKIPPED post-hoc): roll normalization changes ALL bone axes incl. legs,
    # which breaks the leg euler animation tuned to the original axes. World-space arm
    # aiming is axis-agnostic so it doesn't need it. Roll normalization belongs in a
    # FRESH build where animation is authored for the normalized axes.
    # mrb.normalize_bone_rolls(arm)

    # re-bind
    for n, bone in bind.items():
        by_name[n].matrix_world = world[n]
        mrb.bind_segment(by_name[n], arm, bone)
    bpy.context.view_layer.update()

    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[V4] saved: {blend_out}")


if __name__ == "__main__":
    main()
