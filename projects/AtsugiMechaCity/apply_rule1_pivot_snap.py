# -*- coding: utf-8 -*-
"""
apply_rule1_pivot_snap.py — apply RULE ① (pivot = real joint center) to an ALREADY
rigged blend, post-hoc, so we can measure the fix without a full FBX rebuild.

Steps: load blend -> record each mesh's bone + world matrix -> unparent (keep world)
-> snap bone heads to geometry-derived joint centers (mecha_rig_builder.snap_*) ->
re-bind meshes (world preserved) -> save as v3.

Run:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\apply_rule1_pivot_snap.py -- ^
    --in D:\\Temp\\Zaku_AutoRig_v2.blend --out D:\\Temp\\Zaku_AutoRig_v3.blend
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


# import the reusable rig functions
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mecha_rig_builder as mrb  # noqa: E402


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v2.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v3.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    if not arm:
        print("[R1] no armature"); return

    # 1) capture current binding + world transforms
    bind = {}          # mesh_name -> bone
    world = {}         # mesh_name -> matrix_world
    by_name = {}
    for o in scene.objects:
        if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
            bind[o.name] = o.parent_bone
            world[o.name] = o.matrix_world.copy()
            by_name[o.name] = o
    print(f"[R1] captured {len(bind)} bound segments")

    # 2) unparent (keep world transform)
    bpy.ops.object.select_all(action="DESELECT")
    for name in bind:
        by_name[name].select_set(True)
    bpy.context.view_layer.objects.active = by_name[next(iter(bind))]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.context.view_layer.update()
    for name, m in world.items():
        by_name[name].matrix_world = m  # ensure exact restore

    # 3) RULE ① snap pivots to joint centers
    moved = mrb.snap_bones_to_joint_centers(arm, bind, by_name)
    print(f"[R1] pivots snapped ({len(moved)}): {moved}")

    # 4) re-bind segments (world preserved by bind_segment)
    for name, bone in bind.items():
        by_name[name].matrix_world = world[name]
        mrb.bind_segment(by_name[name], arm, bone)
    bpy.context.view_layer.update()

    # 5) save
    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[R1] saved: {blend_out}")


if __name__ == "__main__":
    main()
