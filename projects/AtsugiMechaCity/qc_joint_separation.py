# -*- coding: utf-8 -*-
"""
qc_joint_separation.py — RULE ④: joint separation QC gate (diagnostic + reusable).

For each articulated joint, sweep the child bone through a test range and measure
how far the CHILD segment mesh pulls away from its PARENT segment mesh. Rigid
bone-parenting with an off-axis pivot makes the child swing out of its socket; this
quantifies that gap so we never again ship a detached arm / split thigh on a
"numbers look fine" basis (T031/T032 discipline).

Metric per joint:
  d0   = min surface distance child<->parent at REST (≈0 if they touch/overlap)
  dmax = max over the sweep of that min distance
  gap_growth = dmax - d0   ->  FAIL if gap_growth > tol (tol = ratio * model_height)

Run (diagnostic on existing rigged blend):
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background `
    --python projects\\AtsugiMechaCity\\qc_joint_separation.py -- --blend D:\\Temp\\Zaku_AutoRig_v2.blend
"""
import bpy
import sys
import math
import mathutils
from mathutils import kdtree

_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag, default=None):
    if flag in _args:
        i = _args.index(flag)
        if i + 1 < len(_args):
            return _args[i + 1]
    return default


# Test sweep: degrees per axis we probe (covers a typical walking range).
SWEEP_DEG = [-20, -12, -6, 6, 12, 20]
TOL_RATIO = 0.04           # gap > 4% of model height = separation FAIL
MAX_VERTS = 1200           # subsample meshes for speed


def _world_verts(obj, cap=MAX_VERTS):
    mw = obj.matrix_world
    vs = obj.data.vertices
    step = max(1, len(vs) // cap)
    return [mw @ vs[i].co for i in range(0, len(vs), step)]


def _min_surface_dist(child_objs, parent_kd):
    """min distance from any child vertex to the parent vertex cloud."""
    best = 1e9
    for obj in child_objs:
        for v in _world_verts(obj):
            _co, _idx, dist = parent_kd.find(v)
            if dist < best:
                best = dist
    return best


def _build_kd(objs):
    pts = []
    for o in objs:
        pts.extend(_world_verts(o))
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd


def joint_separation_gate(arm_obj, meshes, tol_ratio=TOL_RATIO):
    """Return {"pass": bool, "checks": [...], "verdict": str} for joint integrity."""
    # model height for tolerance
    lo = mathutils.Vector((1e9,) * 3)
    hi = mathutils.Vector((-1e9,) * 3)
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    height = (hi - lo).z
    tol = tol_ratio * height

    # group meshes by the bone they're parented to
    by_bone = {}
    for o in meshes:
        if o.parent is o and False:
            pass
        if o.parent_type == "BONE" and o.parent_bone:
            by_bone.setdefault(o.parent_bone, []).append(o)

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones

    checks = []
    for bone in arm_obj.data.bones:
        child_objs = by_bone.get(bone.name)
        if not child_objs:
            continue
        parent = bone.parent
        # climb to a parent bone that actually has bound meshes
        parent_objs = None
        while parent is not None:
            if by_bone.get(parent.name):
                parent_objs = by_bone[parent.name]
                break
            parent = parent.parent
        if not parent_objs:
            continue

        parent_kd = _build_kd(parent_objs)
        pbone = pb.get(bone.name)
        if not pbone:
            continue
        # mute its limit so we probe the geometry, not the (current) limit
        muted = [c for c in pbone.constraints if c.type == "LIMIT_ROTATION"]
        for c in muted:
            c.mute = True
        pbone.rotation_mode = "XYZ"
        rest = pbone.rotation_euler.copy()

        # rest distance
        pbone.rotation_euler = rest
        bpy.context.view_layer.update()
        d0 = _min_surface_dist(child_objs, parent_kd)

        dmax = d0
        worst = (0, "x", 0.0)
        for ax_i, ax in enumerate("xyz"):
            for deg in SWEEP_DEG:
                e = rest.copy()
                e[ax_i] = rest[ax_i] + math.radians(deg)
                pbone.rotation_euler = e
                bpy.context.view_layer.update()
                d = _min_surface_dist(child_objs, parent_kd)
                if d > dmax:
                    dmax = d
                    worst = (deg, ax, d)
        pbone.rotation_euler = rest
        for c in muted:
            c.mute = False

        gap_growth = dmax - d0
        ok = gap_growth <= tol
        checks.append({
            "joint": bone.name,
            "parent": parent.name,
            "d0": round(d0, 3),
            "gap_growth": round(gap_growth, 3),
            "worst": f"{worst[1]}{worst[0]:+d}deg->{worst[2]:.2f}m",
            "tol": round(tol, 3),
            "pass": ok,
        })

    bpy.ops.object.mode_set(mode="OBJECT")
    all_pass = all(c["pass"] for c in checks) if checks else False
    return {
        "pass": all_pass,
        "tol": round(tol, 3),
        "checks": checks,
        "verdict": "JOINTS OK" if all_pass else "JOINT SEPARATION: " + ", ".join(
            c["joint"] for c in checks if not c["pass"]),
    }


def main():
    blend = _arg("--blend", "D:/Temp/Zaku_AutoRig_v2.blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    arm = next((o for o in bpy.context.scene.objects if o.type == "ARMATURE"), None)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not arm:
        print("[QC4] no armature"); return
    res = joint_separation_gate(arm, meshes)
    print(f"[QC4] model joint-separation gate (tol={res['tol']}m)", flush=True)
    print(f"[QC4] {'JOINT':14s} {'PARENT':10s} {'d0':>6s} {'gap_growth':>11s} {'worst':>22s}  PASS")
    for c in sorted(res["checks"], key=lambda x: -x["gap_growth"]):
        print(f"[QC4] {c['joint']:14s} {c['parent']:10s} {c['d0']:6.2f} "
              f"{c['gap_growth']:11.2f} {c['worst']:>22s}  {'OK' if c['pass'] else 'FAIL'}",
              flush=True)
    print(f"[QC4] VERDICT: {res['verdict']}", flush=True)


if __name__ == "__main__":
    main()
