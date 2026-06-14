# -*- coding: utf-8 -*-
"""
resegment_left_arm_v5.py — fix the SOURCE-segmentation blocker: the left arm is one
merged segment (part_10) on UpperArm_L, so it can't bend/pose. Split it at the elbow
into upper + forearm (mirroring the right arm's split), rebind, then re-apply RULE①
pivots + shoulder-shield follower. Output v5.

Elbow X derived from the right arm: part_9 upper x[2.03,7.83], part_11 forearm
x[7.61,9.88] -> elbow at ~72% shoulder->hand. Left part_10 x[-8.22,-1.41] -> -6.31.

Run:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\resegment_left_arm_v5.py -- ^
    --in D:\\Temp\\Zaku_AutoRig_v2.blend --out D:\\Temp\\Zaku_AutoRig_v5.blend
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

ELBOW_X = -6.31  # split plane for left arm (72% shoulder->hand, mirrored from right)


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v2.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v5.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)

    # capture bindings + world transforms
    bind, world, by_name = {}, {}, {}
    for o in scene.objects:
        if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
            bind[o.name] = o.parent_bone
            world[o.name] = o.matrix_world.copy()
            by_name[o.name] = o

    # unparent all (keep world)
    bpy.ops.object.select_all(action="DESELECT")
    for n in bind:
        by_name[n].select_set(True)
    bpy.context.view_layer.objects.active = by_name[next(iter(bind))]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.context.view_layer.update()
    for n, m in world.items():
        by_name[n].matrix_world = m

    # --- SPLIT part_10 at the elbow X-plane ---
    p10 = bpy.data.objects.get("part_10")
    if not p10:
        print("[V5] part_10 not found"); return
    import bmesh
    bpy.ops.object.select_all(action="DESELECT")
    p10.select_set(True)
    bpy.context.view_layer.objects.active = p10
    mw = p10.matrix_world
    # select forearm-side verts (world x < ELBOW_X) robustly inside edit mode
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bm = bmesh.from_edit_mesh(p10.data)
    n_sel = 0
    for v in bm.verts:
        v.select_set((mw @ v.co).x < ELBOW_X)
        n_sel += 1 if (mw @ v.co).x < ELBOW_X else 0
    bm.select_flush(True)
    bmesh.update_edit_mesh(p10.data)
    print(f"[V5] selected {n_sel}/{len(bm.verts)} forearm verts (x<{ELBOW_X})")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    # the separated object is the new forearm piece
    new_obj = next((o for o in scene.objects if o.name.startswith("part_10.")), None)
    if not new_obj:
        print("[V5] split produced no new object"); return
    new_obj.name = "part_10_forearm"
    print(f"[V5] split part_10 -> upper({len(p10.data.vertices)}v) + "
          f"part_10_forearm({len(new_obj.data.vertices)}v)")

    # update bind map: upper stays on UpperArm_L, forearm -> LowerArm_L
    bind["part_10"] = "UpperArm_L"
    bind["part_10_forearm"] = "LowerArm_L"
    world["part_10_forearm"] = new_obj.matrix_world.copy()
    by_name["part_10"] = p10
    by_name["part_10_forearm"] = new_obj

    # RULE① pivots (now left arm has a real elbow -> good shoulder+elbow pivots)
    moved = mrb.snap_bones_to_joint_centers(arm, bind, by_name)
    print(f"[V5] ① pivots snapped ({len(moved)})")
    # shoulder-shield follower (arms only)
    rearm = mrb.reassign_plate_armor_to_parent(arm, bind, by_name,
                                               limb_bones=("UpperArm_L", "UpperArm_R"))
    print(f"[V5] plate armor reassigned: {rearm}")

    # rebind all
    for n, bone in bind.items():
        by_name[n].matrix_world = world[n]
        mrb.bind_segment(by_name[n], arm, bone)
    bpy.context.view_layer.update()

    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[V5] saved: {blend_out}")


if __name__ == "__main__":
    main()
