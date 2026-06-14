# -*- coding: utf-8 -*-
"""Blender builder: rig_spec.json -> armature + rigid-parented mesh + joint
motion constraints (LIMIT_ROTATION) + armor_follower (COPY_ROTATION) -> FBX.

Last stage of the mecha auto-rig pipeline:
  classifier -> rig_spec.json -> [GUI edits] -> THIS builder -> rigged FBX

Run inside Blender 5.1:
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" --background \\
    --python mecha_rig_builder.py -- \\
    --spec zaku_rig_spec_edited.json --fbx Gundam/RickDias_Segmentation.fbx \\
    --out-fbx out/Zaku_Rigged.fbx --report out/build_report.json

The motion-constraint logic (joint_constraint_params) is pure Python and is
unit-tested without Blender via `python mecha_rig_builder.py --selftest`. Only
the thin bpy application layer needs Blender to verify.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

DEFAULT_UPRIGHT_DEG = (90.0, 0.0, 0.0)
DEFAULT_TARGET_HEIGHT = 18.0
# Height/width ratio floor for a humanoid mecha standing upright.
# T-pose arm span can exceed height, so 0.7 allows ~1.4:1 width:height.
_UPRIGHT_ASPECT_MIN = 0.7

AXIS_NAMES = ("x", "y", "z")


# --------------------------------------------------------------------------- #
# Pure logic (no bpy) -- unit-testable                                         #
# --------------------------------------------------------------------------- #
def _axis_index(axis: list[float] | tuple) -> int:
    for i, v in enumerate(axis[:3]):
        if abs(float(v)) > 0.5:
            return i
    return 0


def joint_constraint_params(
    jtype: str, axis: list[float] | tuple, limits_deg: dict[str, float]
) -> dict[str, dict[str, Any]]:
    """Map a spec joint to per-axis LIMIT_ROTATION params (degrees).

    Returns {"x"|"y"|"z": {"use": bool, "min": deg, "max": deg}}.
    - hinge:    limit the hinge axis, lock the other two (1-DOF, e.g. elbow/knee)
    - revolute: limit the hinge axis, allow small play on the others
    - ball:     apply limits on all axes (e.g. shoulder/hip)
    - fixed:    lock all axes (rigid armor, no articulation)
    """
    lo = float((limits_deg or {}).get("min", 0.0))
    hi = float((limits_deg or {}).get("max", 0.0))
    lock = {"use": True, "min": 0.0, "max": 0.0}
    lim = {"use": True, "min": lo, "max": hi}
    play = {"use": True, "min": -10.0, "max": 10.0}
    ai = _axis_index(axis)

    if jtype == "fixed":
        return {a: dict(lock) for a in AXIS_NAMES}
    if jtype == "hinge":
        out = {a: dict(lock) for a in AXIS_NAMES}
        out[AXIS_NAMES[ai]] = dict(lim)
        return out
    if jtype == "revolute":
        out = {a: dict(play) for a in AXIS_NAMES}
        out[AXIS_NAMES[ai]] = dict(lim)
        return out
    if jtype == "ball":
        return {a: dict(lim) for a in AXIS_NAMES}
    # unknown -> free (no limit)
    return {a: {"use": False, "min": 0.0, "max": 0.0} for a in AXIS_NAMES}


def load_spec(path: str | Path) -> dict[str, Any]:
    spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if spec.get("schema") != "clawstack.mecha_rig_spec.v1":
        raise ValueError(f"not a mecha_rig_spec.v1: {spec.get('schema')}")
    return spec


def plan_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Build a bpy-free build plan (which mesh -> which bone, followers, joints).
    Lets us validate/inspect the whole rig before touching Blender."""
    bind: dict[str, str] = {}
    followers: list[dict[str, Any]] = []
    issues: list[str] = []
    for s in spec.get("segments") or []:
        name, bone = s.get("name"), s.get("bone")
        if not bone:
            issues.append(f"no_bone:{name}")
            continue
        pt = s.get("part_type", "structural")
        if pt == "armor_follower":
            drv = s.get("driver_bone")
            if not drv:
                issues.append(f"follower_no_driver:{name}")
                continue
            followers.append(
                {"segment": name, "base_bone": bone, "driver_bone": drv,
                 "influence": float(s.get("follow_influence") or 0.5)}
            )
        else:
            bind[name] = bone
    joints = [
        {"child": j.get("child_bone"), "type": j.get("type"),
         "params": joint_constraint_params(j.get("type"), j.get("axis", [1, 0, 0]), j.get("limits_deg", {}))}
        for j in spec.get("joints") or []
    ]
    return {"bind": bind, "followers": followers, "joints": joints, "issues": issues}


# --------------------------------------------------------------------------- #
# Blender application layer (needs bpy)                                        #
# --------------------------------------------------------------------------- #
def _require_bpy() -> None:
    if not HAS_BPY:
        raise RuntimeError("This step requires Blender (run via blender --python).")


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for coll in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass


def _meshes() -> list:
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def _bounds(objs: list):
    import mathutils as mu
    lo = mu.Vector((1e9, 1e9, 1e9))
    hi = mu.Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for corner in o.bound_box:
            w = o.matrix_world @ mu.Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


def import_and_normalize(fbx_path: str, upright_deg, target_height: float):
    clear_scene()
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    # Unparent meshes from FBX armature using CLEAR_KEEP_TRANSFORM
    # (preserves bone-parent transforms). Direct parent=None loses them.
    bpy.ops.object.select_all(action="DESELECT")
    arm_children = [o for o in bpy.context.scene.objects
                    if o.type == "MESH" and o.parent and o.parent.type == "ARMATURE"]
    for o in arm_children:
        o.select_set(True)
    if arm_children:
        bpy.context.view_layer.objects.active = arm_children[0]
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.context.view_layer.update()
    for o in list(bpy.context.scene.objects):
        if o.type == "ARMATURE":
            bpy.data.objects.remove(o, do_unlink=True)
    ms = _meshes()
    if not ms:
        raise RuntimeError("No mesh found in FBX.")
    # Auto-detect orientation: if model is already upright (Z-up) based on
    # world-space bounds, skip any rotation. After parent_clear(KEEP_TRANSFORM)
    # meshes carry inherited rotation — setting rotation_euler=(0,0,0)
    # would REMOVE that inherited rotation and break the model.
    lo_raw, hi_raw = _bounds(ms)
    raw_height = hi_raw.z - lo_raw.z
    raw_width = max(hi_raw.x - lo_raw.x, hi_raw.y - lo_raw.y)
    already_upright = raw_height > raw_width * 0.8
    roots = [o for o in bpy.context.scene.objects if o.parent is None]
    if already_upright:
        print(f"[mecha_rig_builder] FBX already Z-up (H={raw_height:.1f} > W={raw_width:.1f}), keeping existing transforms")
    else:
        for o in roots:
            o.rotation_euler = tuple(math.radians(v) for v in upright_deg)
    bpy.context.view_layer.update()
    lo, hi = _bounds(ms)
    scale = target_height / max(hi.z - lo.z, 1e-4)
    for o in roots:
        o.scale = tuple(c * scale for c in o.scale)
    bpy.context.view_layer.update()
    lo, _ = _bounds(ms)
    for o in roots:
        o.location.z -= float(lo.z)
    bpy.context.view_layer.update()
    for o in ms:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        o.name = o.name.replace(" ", "_")
    bpy.context.view_layer.update()
    return _meshes()


def _eb(arm_data, name, head, tail, parent=None):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail, b.roll = head, tail, 0.0
    if parent is not None:
        b.parent = parent
        b.use_connect = False
    return b


def create_armature(lo, hi):
    """Standard humanoid mecha skeleton (proven Zaku layout)."""
    size = hi - lo
    cx, cy, z0 = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z
    h = max(size.z, 1e-4)
    hx = max(size.x / 2, 1.0)

    def p(fx, fy, fz):
        return mathutils.Vector((cx + hx * fx, cy + size.y * fy, z0 + h * fz))

    ad = bpy.data.armatures.new("Mecha_ArmatureData")
    ao = bpy.data.objects.new("Mecha_Armature", ad)
    bpy.context.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao
    ao.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    root = _eb(ad, "Root", p(0, 0, 0.02), p(0, 0, 0.14))
    hips = _eb(ad, "Hips", p(0, 0, 0.14), p(0, 0, 0.42), root)
    chest = _eb(ad, "Chest", p(0, 0, 0.42), p(0, 0, 0.68), hips)
    neck = _eb(ad, "Neck", p(0, 0, 0.68), p(0, 0, 0.78), chest)
    head = _eb(ad, "Head", p(0, 0, 0.78), p(0, 0, 0.98), neck)
    _eb(ad, "MonoEye", p(0, -0.08, 0.90), p(0, -0.14, 0.90), head)
    lu = _eb(ad, "UpperArm_L", p(-0.25, 0, 0.63), p(-0.57, 0, 0.56), chest)
    ll = _eb(ad, "LowerArm_L", p(-0.57, 0, 0.56), p(-0.84, 0, 0.47), lu)
    _eb(ad, "Hand_L", p(-0.84, 0, 0.47), p(-1.0, 0, 0.42), ll)
    ru = _eb(ad, "UpperArm_R", p(0.25, 0, 0.63), p(0.57, 0, 0.56), chest)
    rl = _eb(ad, "LowerArm_R", p(0.57, 0, 0.56), p(0.84, 0, 0.47), ru)
    _eb(ad, "Hand_R", p(0.84, 0, 0.47), p(1.0, 0, 0.42), rl)
    lul = _eb(ad, "UpperLeg_L", p(-0.16, 0, 0.40), p(-0.26, 0, 0.23), hips)
    lll = _eb(ad, "LowerLeg_L", p(-0.26, 0, 0.23), p(-0.22, 0, 0.08), lul)
    _eb(ad, "Foot_L", p(-0.22, 0, 0.08), p(-0.36, -0.10, 0.02), lll)
    rul = _eb(ad, "UpperLeg_R", p(0.16, 0, 0.40), p(0.26, 0, 0.23), hips)
    rll = _eb(ad, "LowerLeg_R", p(0.26, 0, 0.23), p(0.22, 0, 0.08), rul)
    _eb(ad, "Foot_R", p(0.22, 0, 0.08), p(0.36, -0.10, 0.02), rll)
    bpy.ops.object.mode_set(mode="OBJECT")
    ad.display_type = "STICK"
    ao.show_in_front = True
    return ao


def add_follower_bones(arm_obj, followers: list[dict[str, Any]]) -> None:
    """Create one helper bone per follower armor, parented to its base bone,
    copying the base bone's rest position (pivot ~ base joint)."""
    if not followers:
        return
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_obj.data.edit_bones
    for f in followers:
        base = eb.get(f["base_bone"])
        if not base:
            continue
        hb = eb.new(f"Follow_{f['segment']}")
        hb.head = base.head.copy()
        hb.tail = base.tail.copy()
        hb.parent = base
        hb.use_connect = False
        f["helper_bone"] = hb.name
    bpy.ops.object.mode_set(mode="OBJECT")


def bind_segment(obj, arm_obj, bone_name: str) -> None:
    world = obj.matrix_world.copy()
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    obj.parent = arm_obj
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    obj.matrix_world = world


def apply_joint_constraints(arm_obj, joints: list[dict[str, Any]]) -> list[str]:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    applied = []
    for j in joints:
        pb = arm_obj.pose.bones.get(j["child"]) if j.get("child") else None
        if not pb:
            continue
        for c in list(pb.constraints):
            if c.type == "LIMIT_ROTATION":
                pb.constraints.remove(c)
        c = pb.constraints.new("LIMIT_ROTATION")
        c.owner_space = "LOCAL"
        for ax in AXIS_NAMES:
            pr = j["params"][ax]
            setattr(c, f"use_limit_{ax}", bool(pr["use"]))
            setattr(c, f"min_{ax}", math.radians(pr["min"]))
            setattr(c, f"max_{ax}", math.radians(pr["max"]))
        applied.append(f"{j['child']}:{j['type']}")
    bpy.ops.object.mode_set(mode="OBJECT")
    return applied


def apply_follower_constraints(arm_obj, followers: list[dict[str, Any]]) -> list[str]:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    applied = []
    for f in followers:
        hb = f.get("helper_bone")
        pb = arm_obj.pose.bones.get(hb) if hb else None
        if not pb:
            continue
        c = pb.constraints.new("COPY_ROTATION")
        c.target = arm_obj
        c.subtarget = f["driver_bone"]
        c.influence = max(0.0, min(1.0, float(f["influence"])))
        c.owner_space = "LOCAL"
        c.target_space = "LOCAL"
        applied.append(f"{f['segment']}<-{f['driver_bone']}@{c.influence}")
    bpy.ops.object.mode_set(mode="OBJECT")
    return applied


_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # D:\Clawdbot_Docker_20260125


def _geometric_quality_gate(meshes: list) -> dict[str, Any]:
    """Check visual plausibility of the assembled model.
    Returns {"pass": bool, "checks": [...], "verdict": str}.
    This prevents the false-PASS problem where a technically-complete
    but visually broken model is declared ok."""
    lo, hi = _bounds(meshes)
    sz = hi - lo
    height, width, depth = sz.z, sz.x, sz.y
    checks = []

    aspect = height / max(width, 0.01)
    upright = aspect >= _UPRIGHT_ASPECT_MIN
    checks.append({
        "name": "upright_aspect",
        "value": round(aspect, 2),
        "threshold": _UPRIGHT_ASPECT_MIN,
        "pass": upright,
        "detail": f"H/W={aspect:.2f} ({'upright' if upright else 'FLAT/TOPPLED'})",
    })

    grounded = lo.z < height * 0.05
    checks.append({
        "name": "grounded",
        "value": round(float(lo.z), 2),
        "pass": grounded,
        "detail": f"z_min={lo.z:.2f} ({'grounded' if grounded else 'FLOATING'})",
    })

    symmetry = abs((lo.x + hi.x) / 2) / max(width, 0.01)
    sym_ok = symmetry < 0.15
    checks.append({
        "name": "center_symmetry",
        "value": round(symmetry, 3),
        "threshold": 0.15,
        "pass": sym_ok,
        "detail": f"center_offset_ratio={symmetry:.3f} ({'centered' if sym_ok else 'OFF-CENTER'})",
    })

    all_pass = all(c["pass"] for c in checks)
    return {
        "pass": all_pass,
        "checks": checks,
        "verdict": "GEOMETRY OK" if all_pass else "GEOMETRY FAILED: " + ", ".join(
            c["name"] for c in checks if not c["pass"]
        ),
    }


def render_preview(arm_obj, out_png: str, resolution: tuple[int, int] = (960, 540)) -> str | None:
    """Render a 3-point-lit turntable-front preview of the rigged model.
    Returns the output path on success, None on failure."""
    _require_bpy()
    try:
        scene = bpy.context.scene
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                scene.render.engine = eng
                break
            except TypeError:
                continue
        scene.render.resolution_x, scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = False
        scene.render.image_settings.file_format = "PNG"

        # Camera
        cam_data = bpy.data.cameras.new("Preview_Cam")
        cam_data.lens = 50
        cam_obj = bpy.data.objects.new("Preview_Cam", cam_data)
        bpy.context.collection.objects.link(cam_obj)
        scene.camera = cam_obj
        lo, hi = _bounds([o for o in scene.objects if o.type == "MESH"])
        center = (lo + hi) / 2
        height = max(hi.z - lo.z, 1.0)
        cam_obj.location = (center.x + height * 1.8, center.y - height * 2.8, center.z + height * 0.5)
        direction = center - cam_obj.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        cam_obj.rotation_euler = rot_quat.to_euler()

        # Default gray material for unshaded meshes
        mat = bpy.data.materials.new("Preview_Gray")
        mat.diffuse_color = (0.45, 0.50, 0.48, 1.0)
        for o in scene.objects:
            if o.type == "MESH" and not o.data.materials:
                o.data.materials.append(mat)

        # 3-point lighting (EEVEE watts, not Cycles)
        def _add_light(name, loc, energy, light_type="POINT"):
            ld = bpy.data.lights.new(name, light_type)
            ld.energy = energy
            obj = bpy.data.objects.new(name, ld)
            obj.location = loc
            bpy.context.collection.objects.link(obj)
            return obj

        _add_light("Key", (center.x + height, center.y - height * 1.5, center.z + height * 0.8), 5000)
        _add_light("Fill", (center.x - height, center.y - height * 0.5, center.z + height * 0.4), 2000)
        _add_light("Rim", (center.x - height * 0.3, center.y + height, center.z + height * 0.6), 3000)

        # Background
        world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
        scene.world = world
        if hasattr(world, "use_nodes"):
            try:
                world.use_nodes = True
            except Exception:
                pass
        if world.node_tree:
            bg = world.node_tree.nodes.get("Background")
            if bg:
                bg.inputs["Color"].default_value = (0.12, 0.14, 0.18, 1.0)
                bg.inputs["Strength"].default_value = 0.5

        Path(out_png).parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)
        print(f"[mecha_rig_builder] preview rendered: {out_png}")
        return str(out_png)
    except Exception as e:
        print(f"[mecha_rig_builder] WARN: preview render failed: {e}")
        return None


def notify_telegram(image_path: str | None, report: dict[str, Any]) -> bool:
    """Send preview PNG + build summary to Telegram via project notify_image.py."""
    workspace = str(_PROJECT_ROOT / "data" / "workspace")
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    try:
        from notify_image import send_telegram, send_telegram_text
    except ImportError as e:
        print(f"[mecha_rig_builder] WARN: notify_image import failed: {e}")
        return False

    model = report.get("model", "unknown")
    segs = report.get("segments_bound", 0)
    joints = report.get("joints_constrained", [])
    mono = report.get("mono_eye_scan") or "none"
    ok = report.get("ok", False)
    geo = report.get("geometry_qa", {})
    geo_verdict = geo.get("verdict", "NOT CHECKED")
    verdict = "ALL PASS" if ok else f"FAILED ({geo_verdict})"

    caption = (
        f"Mecha Auto-Rig: {model}\n"
        f"Verdict: {verdict}\n"
        f"Geometry QA: {geo_verdict}\n"
        f"Segments: {segs} | Joints: {len(joints)}\n"
        f"MonoEye: {mono}\n"
        f"Missing: {report.get('segments_missing', [])}"
    )

    sent = False
    if image_path and Path(image_path).exists():
        sent = send_telegram(image_path, caption)
    else:
        sent = send_telegram_text(caption)
    return sent


def _try_bake_mono_eye_scan(arm_obj, profile_name: str | None) -> str | None:
    """Bake a MonoEye scan animation using mono_eye_rig_addon profiles.
    Returns the action name on success, None on skip/failure."""
    if not profile_name:
        return None
    pb = arm_obj.pose.bones.get("MonoEye") if arm_obj.pose else None
    if not pb:
        print("[mecha_rig_builder] WARN: MonoEye bone not found, skipping scan animation")
        return None
    try:
        _here = str(Path(__file__).resolve().parent)
        if _here not in sys.path:
            sys.path.insert(0, _here)
        from mono_eye_rig_addon import load_profile, bake_scan_action
        profile = load_profile(profile_name)
        scan_pitch = profile_name == "dom_2dof"
        bake_scan_action(arm_obj, "MonoEye", profile, scan_pitch=scan_pitch)
        return f"MonoEye_Scan_1s({profile_name})"
    except Exception as e:
        print(f"[mecha_rig_builder] WARN: mono_eye scan bake failed: {e}")
        return None


def build(spec_path, fbx_path, out_fbx, report_path, upright_deg, target_height,
          mono_eye_profile: str | None = None, out_blend: str | None = None,
          notify: bool = False) -> dict[str, Any]:
    _require_bpy()
    spec = load_spec(spec_path)
    plan = plan_from_spec(spec)
    meshes = import_and_normalize(fbx_path, upright_deg, target_height)
    lo, hi = _bounds(meshes)
    arm = create_armature(lo, hi)
    add_follower_bones(arm, plan["followers"])

    bound, missing = [], []
    by_name = {o.name: o for o in meshes}
    for seg, bone in plan["bind"].items():
        o = by_name.get(seg) or by_name.get(seg.replace(" ", "_"))
        if o:
            bind_segment(o, arm, bone)
            bound.append(seg)
        else:
            missing.append(seg)
    for f in plan["followers"]:
        o = by_name.get(f["segment"])
        if o and f.get("helper_bone"):
            bind_segment(o, arm, f["helper_bone"])

    joints_applied = apply_joint_constraints(arm, plan["joints"])
    followers_applied = apply_follower_constraints(arm, plan["followers"])
    scan_action = _try_bake_mono_eye_scan(arm, mono_eye_profile)

    if out_blend:
        Path(out_blend).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))

    if out_fbx:
        Path(out_fbx).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.export_scene.fbx(filepath=str(out_fbx), add_leaf_bones=False)

    # Geometry quality gate — catches visually broken models (false-PASS prevention)
    geo_gate = _geometric_quality_gate(_meshes())

    # Preview render (before report, so path goes into report)
    preview_png = None
    if out_fbx:
        preview_png = render_preview(arm, str(Path(out_fbx).with_suffix(".png")))

    tech_ok = not missing and not plan["issues"]
    visual_ok = geo_gate["pass"]
    report = {
        "schema": "clawstack.mecha_rig_build_report.v1",
        "model": spec.get("model"),
        "segments_bound": len(bound),
        "segments_missing": missing,
        "joints_constrained": joints_applied,
        "followers": followers_applied,
        "mono_eye_scan": scan_action,
        "plan_issues": plan["issues"],
        "geometry_qa": geo_gate,
        "out_fbx": str(out_fbx) if out_fbx else None,
        "out_blend": str(out_blend) if out_blend else None,
        "preview_png": preview_png,
        "ok": tech_ok and visual_ok,
    }

    if notify and report["ok"]:
        report["telegram_sent"] = notify_telegram(preview_png, report)
    elif notify and not report["ok"]:
        report["telegram_sent"] = notify_telegram(None, report)

    if report_path:
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[mecha_rig_builder]", json.dumps(report, ensure_ascii=False))
    return report


def _selftest() -> int:
    """Verify the pure constraint logic without Blender."""
    p = joint_constraint_params("hinge", [1, 0, 0], {"min": -150, "max": 0})
    assert p["x"] == {"use": True, "min": -150.0, "max": 0.0}, p
    assert p["y"]["use"] and p["y"]["min"] == 0 and p["y"]["max"] == 0, p
    assert p["z"]["min"] == 0 and p["z"]["max"] == 0, p
    k = joint_constraint_params("hinge", [1, 0, 0], {"min": 0, "max": 150})
    assert k["x"] == {"use": True, "min": 0.0, "max": 150.0}
    f = joint_constraint_params("fixed", [1, 0, 0], {})
    assert all(f[a] == {"use": True, "min": 0.0, "max": 0.0} for a in AXIS_NAMES), f
    b = joint_constraint_params("ball", [1, 0, 0], {"min": -90, "max": 90})
    assert all(b[a] == {"use": True, "min": -90.0, "max": 90.0} for a in AXIS_NAMES), b
    z = joint_constraint_params("hinge", [0, 0, 1], {"min": -30, "max": 30})
    assert z["z"]["min"] == -30.0 and z["x"]["max"] == 0.0, z  # hinge on Z, X/Y locked
    # MonoEye: Zaku = revolute on Z (yaw ±60°), Dom = ball ±45°
    me_zaku = joint_constraint_params("revolute", [0, 0, 1], {"min": -60, "max": 60})
    assert me_zaku["z"] == {"use": True, "min": -60.0, "max": 60.0}, me_zaku
    assert me_zaku["x"]["min"] == -10.0, me_zaku  # revolute play on off-axes
    me_dom = joint_constraint_params("ball", [0, 0, 1], {"min": -45, "max": 45})
    assert all(me_dom[a] == {"use": True, "min": -45.0, "max": 45.0} for a in AXIS_NAMES), me_dom
    # plan_from_spec: follower needs a driver; structural binds.
    spec = {"schema": "clawstack.mecha_rig_spec.v1",
            "segments": [
                {"name": "part_5", "bone": "Chest", "part_type": "armor_fixed"},
                {"name": "skirt_L", "bone": "Hips", "part_type": "armor_follower", "driver_bone": "UpperLeg_L", "follow_influence": 0.6},
                {"name": "skirt_X", "bone": "Hips", "part_type": "armor_follower"},
            ],
            "joints": [{"child_bone": "LowerArm_R", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": -150, "max": 0}}]}
    plan = plan_from_spec(spec)
    assert plan["bind"] == {"part_5": "Chest"}, plan["bind"]
    assert len(plan["followers"]) == 1 and plan["followers"][0]["driver_bone"] == "UpperLeg_L"
    assert "follower_no_driver:skirt_X" in plan["issues"], plan["issues"]
    assert plan["joints"][0]["params"]["x"]["min"] == -150.0
    print("selftest OK: joint_constraint_params + plan_from_spec (pure logic, no bpy)")
    return 0


def main() -> int:
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    import argparse

    parser = argparse.ArgumentParser(description="Blender mecha rig builder (rig_spec -> rigged FBX)")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--spec")
    parser.add_argument("--fbx")
    parser.add_argument("--out-fbx", dest="out_fbx")
    parser.add_argument("--report")
    parser.add_argument("--upright", default="90,0,0")
    parser.add_argument("--target-height", type=float, default=DEFAULT_TARGET_HEIGHT)
    parser.add_argument("--mono-eye-profile", dest="mono_eye_profile",
                        help="Bake MonoEye scan animation (zaku_1dof | dom_2dof)")
    parser.add_argument("--out-blend", dest="out_blend", help="Save .blend (preserves constraints)")
    parser.add_argument("--notify", action="store_true",
                        help="Send preview PNG + report to Telegram on success")
    a = parser.parse_args(args)

    if a.selftest:
        return _selftest()
    if not a.spec or not a.fbx:
        parser.error("--spec and --fbx required (or --selftest)")
    upright = tuple(float(v) for v in a.upright.split(","))
    build(a.spec, a.fbx, a.out_fbx, a.report, upright, a.target_height,
          mono_eye_profile=a.mono_eye_profile, out_blend=a.out_blend,
          notify=a.notify)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
