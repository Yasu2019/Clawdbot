# -*- coding: utf-8 -*-
"""
apply_joint_cores_v6.py — RULE ②: add overlapping joint cores (knee/elbow cylinders,
hip spheres) to v5 -> v6, filling the rigid-hinge gap that shows as a "cut" at the
left knee (and elsewhere) when the joint bends.

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
import mecha_rig_builder as mrb  # noqa: E402


def main():
    blend_in = _arg("--in", "D:/Temp/Zaku_AutoRig_v5.blend")
    blend_out = _arg("--out", "D:/Temp/Zaku_AutoRig_v6.blend")
    bpy.ops.wm.open_mainfile(filepath=blend_in)
    scene = bpy.context.scene
    arm = next((o for o in scene.objects if o.type == "ARMATURE"), None)
    if not arm:
        print("[V6] no armature"); return

    bind, by_name = {}, {}
    for o in scene.objects:
        if o.type == "MESH" and o.parent_type == "BONE" and o.parent_bone:
            bind[o.name] = o.parent_bone
            by_name[o.name] = o

    created = mrb.add_joint_cores(arm, bind, by_name)
    print(f"[V6] joint cores created ({len(created)}): {created}")

    Path(blend_out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_out)
    print(f"[V6] saved: {blend_out}")


if __name__ == "__main__":
    main()
