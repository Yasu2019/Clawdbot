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
# BUGFIX (was 'min closest distance' -> missed visible gaps): we now measure how far
# the CONTACT PATCH opens. A rigid hinge keeps ONE edge touching (min dist ~0) while
# the opposite edge opens a visible gap; the old metric saw the touching edge and
# falsely PASSED. We instead track the verts that touch at rest and measure their
# MAX separation across the sweep (the opening), plus a rest-gap check.
CONTACT_RATIO = 0.018      # verts within 1.8% of height at rest = the contact patch
TOL_RATIO = 0.022          # contact-patch opening > 2.2% of height = visible gap FAIL
MAX_VERTS = 1500           # subsample meshes for speed


def _sample_indices(obj, cap=MAX_VERTS):
    n = len(obj.data.vertices)
    step = max(1, n // cap)
    return list(range(0, n, step))


def _world_verts(obj, cap=MAX_VERTS):
    mw = obj.matrix_world
    vs = obj.data.vertices
    return [mw @ vs[i].co for i in _sample_indices(obj, cap)]


def _build_kd(objs):
    pts = []
    for o in objs:
        pts.extend(_world_verts(o))
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd


def _min_dist(child_objs, parent_kd):
    """Global closest approach child<->parent (used only for the rest-gap check)."""
    best = 1e9
    for obj in child_objs:
        for v in _world_verts(obj):
            d = parent_kd.find(v)[2]
            if d < best:
                best = d
    return best


def _contact_patch(child_objs, parent_kd, thresh):
    """Verts (obj, vertex_index) of the child that TOUCH the parent at the current
    pose (within thresh). This is the face that must stay closed as the joint moves."""
    patch = []
    for obj in child_objs:
        mw = obj.matrix_world
        for i in _sample_indices(obj):
            if parent_kd.find(mw @ obj.data.vertices[i].co)[2] < thresh:
                patch.append((obj, i))
    return patch


def _patch_max_open(patch, parent_kd):
    """Max distance of the (rest-)contact verts to the parent now — i.e. how far the
    contact face has OPENED. Re-reads the same vertex indices after posing."""
    m = 0.0
    for obj, i in patch:
        d = parent_kd.find(obj.matrix_world @ obj.data.vertices[i].co)[2]
        if d > m:
            m = d
    return m


def joint_separation_gate(arm_obj, meshes, tol_ratio=TOL_RATIO):
    """Return {"pass": bool, "checks": [...], "verdict": str} for joint integrity.
    Measures CONTACT-PATCH OPENING (visible gap), not closest distance."""
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
    contact_thresh = CONTACT_RATIO * height

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

        # REST: does the joint even touch? + capture the contact patch.
        pbone.rotation_euler = rest
        bpy.context.view_layer.update()
        rest_min = _min_dist(child_objs, parent_kd)
        patch = _contact_patch(child_objs, parent_kd, contact_thresh)

        if rest_min > contact_thresh:
            # parts don't touch at rest -> a STATIC gap already exists
            pbone.rotation_euler = rest
            for c in muted:
                c.mute = False
            checks.append({
                "joint": bone.name, "parent": parent.name,
                "rest_gap": round(rest_min, 3), "open": 0.0,
                "worst": "rest (static gap)", "tol": round(tol, 3),
                "n_patch": 0, "pass": False,
            })
            continue

        # SWEEP: how far does the contact face OPEN? (max separation of patch verts)
        opening = 0.0
        worst = (0, "x", 0.0)
        for ax_i, ax in enumerate("xyz"):
            for deg in SWEEP_DEG:
                e = rest.copy()
                e[ax_i] = rest[ax_i] + math.radians(deg)
                pbone.rotation_euler = e
                bpy.context.view_layer.update()
                op = _patch_max_open(patch, parent_kd)
                if op > opening:
                    opening = op
                    worst = (deg, ax, op)
        pbone.rotation_euler = rest
        for c in muted:
            c.mute = False

        # opening beyond the contact band = the visible gap
        gap = max(0.0, opening - contact_thresh)
        ok = gap <= tol
        checks.append({
            "joint": bone.name,
            "parent": parent.name,
            "rest_gap": round(rest_min, 3),
            "open": round(gap, 3),
            "worst": f"{worst[1]}{worst[0]:+d}deg->{worst[2]:.2f}m",
            "tol": round(tol, 3),
            "n_patch": len(patch),
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
    print(f"[QC4] contact-patch-opening gate (tol={res['tol']}m = visible gap)", flush=True)
    print(f"[QC4] {'JOINT':14s} {'PARENT':10s} {'rest_gap':>8s} {'open':>6s} {'worst':>22s} {'patch':>6s}  PASS")
    for c in sorted(res["checks"], key=lambda x: -x["open"]):
        print(f"[QC4] {c['joint']:14s} {c['parent']:10s} {c['rest_gap']:8.2f} "
              f"{c['open']:6.2f} {c['worst']:>22s} {c['n_patch']:6d}  {'OK' if c['pass'] else 'FAIL'}",
              flush=True)
    print(f"[QC4] VERDICT: {res['verdict']}", flush=True)


if __name__ == "__main__":
    main()
