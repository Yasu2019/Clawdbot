# -*- coding: utf-8 -*-
"""
apply_joint_cores_v6.py — RULE ② (auto-grow): add sphere joint cores to v5 -> v6 and
GROW them until the fixed RULE④ gate (contact-patch opening) passes for the leg joints
(hip/knee/ankle). This closes the thigh/knee 'cut' on any segmentation, validated by
the gate rather than by eye.

Run:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\apply_joint_cores_v6.py -- ^
    --in D:\\Temp\\Zaku_AutoRig_v5.blend --out D:\\Temp\\Zaku_AutoRig_v6.blend
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
import mecha_rig_builder as mrb       # noqa: E402
import qc_joint_separation as qc      # noqa: E402

LEG_JOINTS = {"UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R", "Foot_L", "Foot_R"}
SCALES = [0.85, 1.2, 1.6, 2.0, 2.5]


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v5.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v6.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)

    def bnames():
        bind, by_name = {}, {}
        for o in scene.objects:
            if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
                bind[o.name] = o.parent_bone
                by_name[o.name] = o
        return bind, by_name

    fixed = _arg("--scale")
    if fixed is not None:
        bind, by_name = bnames()
        mrb.add_joint_cores(arm, bind, by_name, radius_scale=float(fixed))
        bpy.ops.object.mode_set(mode="OBJECT")
        Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_out)
        print(f"[V6] saved {blend_out} (fixed radius_scale={fixed})")
        return

    best_scale = SCALES[-1]
    for scale in SCALES:
        bind, by_name = bnames()
        created = mrb.add_joint_cores(arm, bind, by_name, radius_scale=scale)
        bpy.ops.object.mode_set(mode="OBJECT")
        meshes = [o for o in scene.objects if o.type == "MESH"]
        res = qc.joint_separation_gate(arm, meshes)
        bad = [c["joint"] for c in res["checks"]
               if c["joint"] in LEG_JOINTS and not c["pass"]]
        worst = max((c["open"] for c in res["checks"] if c["joint"] in LEG_JOINTS),
                    default=0.0)
        print(f"[V6] scale={scale}: {len(created)} cores, leg worst open={worst:.2f}m, "
              f"leg fails={bad}", flush=True)
        if not bad:
            best_scale = scale
            break
        best_scale = scale

    # ensure final cores at the chosen scale, rest pose, save
    bind, by_name = bnames()
    mrb.add_joint_cores(arm, bind, by_name, radius_scale=best_scale)
    bpy.ops.object.mode_set(mode="OBJECT")
    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[V6] saved {blend_out} (radius_scale={best_scale})")


if __name__ == "__main__":
    main()
